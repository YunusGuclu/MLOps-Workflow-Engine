# workflow/tasks.py
import os
import pandas as pd
import joblib
import numpy as np
from django.utils import timezone
from celery import shared_task
from django.core.files import File
from django.db import transaction

from .models import Workflow, WorkflowStep, TrainingMetric, TrainingResult


def _normalize_wf_id(wf_id):
    """Chain çıktısı vs. geldiğinde id'yi toparla."""
    if isinstance(wf_id, int):
        return wf_id
    if isinstance(wf_id, dict):
        for k in ('workflow_id', 'id', 'workflow'):
            if k in wf_id:
                try:
                    return int(wf_id[k])
                except Exception:
                    pass
    try:
        return int(wf_id)
    except Exception:
        return None
    
import time
from django.conf import settings

def _debug_delay():
    sec = getattr(settings, 'DEBUG_STEP_DELAY_SEC', 0) or 0
    if sec > 0:
        time.sleep(float(sec))

@shared_task(bind=True)
def upload_task(self, workflow_id, *args, **kwargs):
    workflow_id = _normalize_wf_id(workflow_id)
    if workflow_id is None:
        return
    wf = Workflow.objects.filter(id=workflow_id).first()
    if not wf:
        return

    step = WorkflowStep.objects.create(
        workflow=wf,
        step_name='upload',
        status='PREPROCESSING',
        params=wf.config,
        started_at=timezone.now(),
        task_id=self.request.id
        
    )
    try:
        _debug_delay()
        uploaded_path = wf.dataset.file.path
        step.result = {'uploaded_path': uploaded_path}
        step.status = 'COMPLETED'
        step.completed_at = timezone.now()
        step.save()

        # WEB'den direkt çağrıldıysa zinciri elle yürüt
        if not getattr(self.request, "chain", None):
            preprocess_task.delay(workflow_id)

    except Exception as e:
        step.status = 'FAILED'
        step.result = {'error': str(e)}
        step.completed_at = timezone.now()
        step.save()
        wf.status = 'FAILED'
        wf.save()
        raise


@shared_task(bind=True)
def preprocess_task(self, workflow_id, *args, **kwargs):
    workflow_id = _normalize_wf_id(workflow_id)
    if workflow_id is None:
        return
    wf = Workflow.objects.filter(id=workflow_id).first()
    if not wf:
        return

    wf.status = 'PREPROCESSING'
    wf.save()

    step = WorkflowStep.objects.create(
        workflow=wf,
        step_name='preprocess',
        status='PREPROCESSING',
        params=wf.config,
        started_at=timezone.now(),
        task_id=self.request.id
    )

    try:
        path = wf.dataset.file.path
        df = pd.read_csv(path).dropna()
        X, y = df.iloc[:, :-1], df.iloc[:, -1]
        _debug_delay()
        proc_dir = os.path.join(os.path.dirname(path), 'processed')
        os.makedirs(proc_dir, exist_ok=True)
        proc_path = os.path.join(proc_dir, f'{wf.id}_data.pkl')
        pd.to_pickle((X, y), proc_path)

        step.result = {'processed_path': proc_path}
        step.status = 'COMPLETED'
        step.completed_at = timezone.now()
        step.save()

        # WEB'den direkt çağrıldıysa zinciri elle yürüt
        if not getattr(self.request, "chain", None):
            train_task.delay(wf.id)

    except Exception as e:
        step.status = 'FAILED'
        step.result = {'error': str(e)}
        step.completed_at = timezone.now()
        step.save()
        wf.status = 'FAILED'
        wf.save()
        raise


@shared_task(bind=True)
def train_task(self, workflow_id, *args, **kwargs):
    workflow_id = _normalize_wf_id(workflow_id)
    if workflow_id is None:
        return
    wf = Workflow.objects.filter(id=workflow_id).first()
    if not wf:
        return

    # Aynı WF için sonuç varsa tekrar eğitme (web'de kullanıcı yeniden başlatırsa zaten yeni WF oluşturur)
    if wf.status in ['TRAINING', 'COMPLETED'] and TrainingResult.objects.filter(workflow=wf).exists():
        return

    wf.status = 'TRAINING'
    wf.save()

    step = WorkflowStep.objects.create(
        workflow=wf,
        step_name='train',
        status='TRAINING',
        params=wf.config,
        started_at=timezone.now(),
        task_id=self.request.id
    )

    try:
        pre = wf.steps.filter(step_name='preprocess').order_by('-started_at').first()
        if not pre:
            raise ValueError("Preprocess step bulunamadı.")
        X, y = pd.read_pickle(pre.result['processed_path'])

        from sklearn.model_selection import train_test_split
        tst = float(wf.config.get('test_size', 0.2))
        rnd = int(wf.config.get('random_state', 42))
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=tst, random_state=rnd
        )

        p = wf.config
        epochs = int(p.get('epochs', 1))
        lr = float(p.get('learning_rate', 0.01))
        bs = int(p.get('batch_size', 32))
        model_name = p['model']

      
        if model_name == 'LR':
            from sklearn.linear_model import SGDClassifier
            model = SGDClassifier(
                loss='log_loss',
                max_iter=1,
                warm_start=True,
                learning_rate='optimal',
                eta0=lr,
                random_state=rnd
            )
        elif model_name == 'SVM':
            from sklearn.linear_model import SGDClassifier
            model = SGDClassifier(
                loss='hinge',
                max_iter=1,
                warm_start=True,
                learning_rate='optimal',
                eta0=lr,
                random_state=rnd
            )
        elif model_name == 'PER':
            from sklearn.linear_model import Perceptron
            model = Perceptron(
                max_iter=1,
                warm_start=True,
                random_state=rnd
            )
        elif model_name == 'PA':
            from sklearn.linear_model import PassiveAggressiveClassifier
            model = PassiveAggressiveClassifier(
                max_iter=1,
                warm_start=True,
                random_state=rnd
            )
        elif model_name == 'MLP':
            from sklearn.neural_network import MLPClassifier
            model = MLPClassifier(
                hidden_layer_sizes=(100,),
                solver='sgd',
                learning_rate_init=lr,
                batch_size=bs,
                max_iter=1,
                warm_start=True,
                random_state=rnd
            )
        else:
            raise ValueError(f'Bilinmeyen model: {model_name}')
   
        _debug_delay()
        classes = np.unique(y_train)
        for ep in range(1, epochs + 1):
            model.partial_fit(X_train, y_train, classes=classes)
            train_acc = model.score(X_train, y_train)
            val_acc = model.score(X_test, y_test)

            TrainingMetric.objects.create(
                workflow=wf,
                epoch=ep,
                metrics={'train_acc': train_acc, 'val_acc': val_acc}
            )

        media_dir = os.path.join(os.path.dirname(pre.result['processed_path']), '..', 'models')
        os.makedirs(media_dir, exist_ok=True)
        model_filename = f'workflow_{wf.id}_{model_name}.joblib'
        local_fp = os.path.join(media_dir, model_filename)
        joblib.dump(model, local_fp)

        with open(local_fp, 'rb') as f:
            djf = File(f)
            with transaction.atomic():
                try:
                    tr = TrainingResult.objects.select_for_update().get(workflow=wf)
                except TrainingResult.DoesNotExist:
                    tr = TrainingResult(workflow=wf)

                tr.summary = {'train_acc': train_acc, 'val_acc': val_acc}
                tr.model_file.save(model_filename, djf, save=False)
                tr.save()

        step.result = {'model_file': tr.model_file.name}
        step.status = 'COMPLETED'
        step.completed_at = timezone.now()
        step.save()

        wf.status = 'COMPLETED'
        wf.save()

    except Exception as e:
        step.status = 'FAILED'
        step.result = {'error': str(e)}
        step.completed_at = timezone.now()
        step.save()

        wf.status = 'FAILED'
        wf.save()
        raise
