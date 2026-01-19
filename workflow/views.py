# workflow/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django_celery_results.models import TaskResult

from .forms import DataUploadForm, ModelConfigForm
from .models import Workflow, WorkflowStep, TrainingMetric, TrainingResult
from .tasks import preprocess_task, upload_task,train_task
from django.views.generic import ListView
from .models import Workflow, WorkflowStep
from django_celery_results.models import TaskResult
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.utils import timezone

class WorkflowCreateView(View):
    def get(self, request):
        # Yeni workflow formunu göster
        return render(request, 'workflow/create.html', {
            'upload_form': DataUploadForm(),
            'config_form': ModelConfigForm()
        })

    def post(self, request):
        # Form gönderildiğinde işle
        upload_form = DataUploadForm(request.POST, request.FILES)
        config_form = ModelConfigForm(request.POST)
        if upload_form.is_valid() and config_form.is_valid():
            ds = upload_form.save()
            cfg = config_form.cleaned_data
            config = {
                'model': cfg.pop('model'),
                **cfg
            }
            wf = Workflow.objects.create(
                name=f'WF {ds.id}',
                dataset=ds,
                config=config
            )
            upload_task.delay(wf.id)
            return redirect('workflow:monitor', workflow_id=wf.id)

        # Hata varsa formu tekrar göster
        return render(request, 'workflow/create.html', {
            'upload_form': upload_form,
            'config_form': config_form
        })

class MonitorView(View):
    def get(self, request, workflow_id):
        wf = get_object_or_404(Workflow, id=workflow_id)
        return render(request, 'workflow/monitor.html', {'workflow': wf})

    def post(self, request, workflow_id):
        """
        POST aksiyonları:
        - action=restart : mevcut zinciri aynen yeniden başlat.
        - action=compose : dataset ve train (config) kaynaklarını farklı WF'lerden seç;
                          zinciri BAŞTAN (upload→preprocess→train) çalıştır.
        """
        old_wf = get_object_or_404(Workflow, id=workflow_id)
        action = request.POST.get('action', 'restart')

        if action == 'restart':
            new_wf = Workflow.objects.create(
                name    = old_wf.name,
                dataset = old_wf.dataset,
                config  = old_wf.config
            )
            upload_task.delay(new_wf.id)
            return redirect('workflow:monitor', workflow_id=new_wf.id)

        elif action == 'compose':
            dataset_src_id = (request.POST.get('dataset_wf') or '').strip()
            train_src_id   = (request.POST.get('train_wf')   or '').strip()

            def _wf_or_default(src_id: str, default: Workflow) -> Workflow:
                try:
                    sid = int(src_id)
                    return Workflow.objects.get(id=sid)
                except Exception:
                    return default

            dataset_src = _wf_or_default(dataset_src_id, old_wf)
            train_src   = _wf_or_default(train_src_id,   old_wf)

            # Yeni Workflow: dataset = dataset_src.dataset, config = train_src.config
            new_wf = Workflow.objects.create(
                name    = f'COMPOSED (dataset #{dataset_src.id}, config #{train_src.id})',
                dataset = dataset_src.dataset,
                config  = train_src.config
            )

            # Tüm zinciri baştan çalıştır (upload -> preprocess -> train)
            upload_task.delay(new_wf.id)

            return redirect('workflow:monitor', workflow_id=new_wf.id)

        return redirect('workflow:monitor', workflow_id=old_wf.id)



class StepsAPIView(View):
    """WorkflowStep + ilgili Celery TaskResult bilgisini döner"""
    def get(self, request, workflow_id):
        steps = WorkflowStep.objects.filter(workflow_id=workflow_id).order_by('started_at')
        data = []
        for step in steps:
            tr = TaskResult.objects.filter(task_id=step.task_id).first()
            data.append({
                'step_name':             step.step_name,
                'step_status':           step.status,
                'step_status_display':   step.get_status_display(),
                'started_at':            step.started_at.isoformat() if step.started_at else None,
                'completed_at':          step.completed_at.isoformat() if step.completed_at else None,
                'celery_status':         tr.status if tr else None,
                'date_done':             tr.date_done.isoformat() if tr and tr.date_done else None,
                'celery_result':         tr.result if tr else None,
            })
        return JsonResponse(data, safe=False)
    
class ResultAPIView(View):
    """WorkflowResult(summary + model_file.url) döner"""
    def get(self, request, workflow_id):
        wf = get_object_or_404(Workflow, id=workflow_id)
        try:
            res = wf.result  # OneToOne
            return JsonResponse({
                'train_acc': res.summary.get('train_acc'),
                'val_acc':   res.summary.get('val_acc'),
                'model_url': res.model_file.url,
            })
        except TrainingResult.DoesNotExist:
            # Henüz sonuç yok
            return JsonResponse({}, status=204)
        
class MetricsAPIView(View):
    def get(self, request, workflow_id):

        # 1) En son train adımını bul
        last_train: WorkflowStep = (
            WorkflowStep.objects
                         .filter(workflow_id=workflow_id, step_name='train')
                         .order_by('-started_at')
                         .first()
        )
        
        # 2) Eğer varsa, o adımdan itibaren eklenen metrikleri al
        if last_train:
            qs = TrainingMetric.objects.filter(
                workflow_id=workflow_id,
                timestamp__gte=last_train.started_at
            ).order_by('epoch')
        else:
            qs = TrainingMetric.objects.none()
        
        # 3) JSON olarak dön
        data = [{'epoch': m.epoch, **m.metrics} for m in qs]
        return JsonResponse(data, safe=False)

class WorkflowStatusAPIView(View):
    def get(self, request, workflow_id):
        wf = get_object_or_404(Workflow, id=workflow_id)
        return JsonResponse({
            'status': wf.status,
            'status_display': wf.get_status_display()
        })

class WorkflowListView(ListView):
    model = Workflow
    template_name = 'workflow/list.html'
    context_object_name = 'workflows'
    paginate_by = 50

    def get_queryset(self):
        qs = Workflow.objects.all().select_related('result')
        # Filtre: ?model=LR vb.
        model_code = self.request.GET.get('model')
        if model_code:
            qs = qs.filter(config__model=model_code)

        # Sıralama: ?sort=train_asc / train_desc / val_asc / val_desc
        sort = self.request.GET.get('sort')
        if sort == 'train_asc':
            qs = qs.order_by('result__summary__train_acc')
        elif sort == 'train_desc':
            qs = qs.order_by('-result__summary__train_acc')
        elif sort == 'val_asc':
            qs = qs.order_by('result__summary__val_acc')
        elif sort == 'val_desc':
            qs = qs.order_by('-result__summary__val_acc')
        else:
            qs = qs.order_by('-created_at')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Sidebar’daki modelleri al
        used_models = Workflow.objects.values_list('config__model', flat=True).distinct()
        # Form’daki kod/etiket eşleşmesini kullan
        ctx['models'] = [
            (code, label)
            for code, label in ModelConfigForm.MODEL_CHOICES
            if code in used_models
        ]
        ctx['current_model'] = self.request.GET.get('model','')
        ctx['current_sort']  = self.request.GET.get('sort','')
        return ctx
    
from .queue_client import (
    _http_get_json,
    _rbmq_cfg,
    _rbmq_queues,
    _rbmq_overview,
    _rbmq_queue_detail,
)

@method_decorator(never_cache, name='dispatch')
class QueueDashboardView(View):
    def get(self, request):
        return render(request, 'workflow/queue.html', {"settings": settings})


@method_decorator(never_cache, name='dispatch')
class QueueStatusAPIView(View):
    def get(self, request):
        overview = _rbmq_overview()
        all_queues = _rbmq_queues()
        _, _, _, _, qname = _rbmq_cfg()
        qdetail  = _rbmq_queue_detail(qname)

        errors = []
        for label, obj in (("overview", overview), ("queues", all_queues), ("focus_queue", qdetail)):
            if isinstance(obj, dict) and obj.get("error"):
                errors.append(f"{label}: {obj['error']}")

        queues = []
        if isinstance(all_queues, list):
            for q in all_queues:
                name = q.get("name") or q.get("queue")
                if name == qname:
                    queues.append(q)

        # --- SON 9 GÖREV + step eşlemesi ---
        qs = TaskResult.objects.order_by('-date_done').values(
            'task_id', 'status', 'date_done', 'task_name'
        )[:9]
        ids = [r['task_id'] for r in qs]

        # task_id -> step_name (upload / preprocess / train)
        step_map = {
            s.task_id: s.step_name
            for s in WorkflowStep.objects.filter(task_id__in=ids)
        }

        def infer_step(task_name: str) -> str | None:
            if not task_name:
                return None
            low = task_name.lower()
            if 'upload' in low: return 'upload'
            if 'preprocess' in low: return 'preprocess'
            if 'train' in low: return 'train'
            return None

        recent_tasks = []
        for r in qs:
            step = step_map.get(r['task_id']) or infer_step(r['task_name'] or '')
            # Gösterim için okunur ad
            if step:
                step_label = step.title()  # Upload/Preprocess/Train
            else:
                step_label = '—'
            # Aynı payload’ı koru + ekstra alanlar
            recent_tasks.append({
                'task_id':   r['task_id'],
                'status':    r['status'],
                'date_done': r['date_done'],
                'name':      r['task_name'],   
                'step':      step,             
                'step_label': step_label,      
            })

        return JsonResponse({
            "overview": overview,
            "queues": queues,
            "focus_queue": qdetail,
            "recent_tasks": recent_tasks,   
            "errors": errors,
        })

from django.utils.dateparse import parse_datetime

def _serialize_step(step):
    """WorkflowStep + TaskResult (varsa) birleştir."""
    tr = TaskResult.objects.filter(task_id=step.task_id).first()
    return {
        "step_name": step.step_name,
        "step_status": step.status,                     # PENDING/PREPROCESSING/TRAINING/COMPLETED/FAILED
        "step_status_display": step.get_status_display(),
        "started_at": step.started_at.isoformat() if step.started_at else None,
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        "task_id": step.task_id,
        # Celery tarafı (django_celery_results)
        "celery_status": tr.status if tr else None,     # PENDING/STARTED/SUCCESS/FAILURE/RETRY
        "date_started": tr.date_started.isoformat() if tr and tr.date_started else None,
        "date_done": tr.date_done.isoformat() if tr and tr.date_done else None,
        "worker": tr.worker if tr else None,
        "task_name": tr.task_name if tr else None,
    }

@method_decorator(never_cache, name='dispatch')
class QueueWorkflowsAPIView(View):
    """
    Queue ekranına canlı 'workflow adımları' besleyen API.
    ?limit=10 (default)
    ?since=2025-08-08T10:00:00Z  (opsiyonel, ISO)
    """
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        since = request.GET.get('since')
        qs = Workflow.objects.all().order_by('-created_at')
        if since:
            dt = parse_datetime(since)
            if dt:
                qs = qs.filter(created_at__gte=dt)
        qs = qs.select_related('result')[:max(1, min(limit, 50))]

        data = []
        for wf in qs:
            steps = WorkflowStep.objects.filter(workflow=wf).order_by('started_at', 'id')
            data.append({
                "workflow_id": wf.id,
                "name": wf.name,
                "status": wf.status,
                "status_display": wf.get_status_display(),
                "created_at": wf.created_at.isoformat() if wf.created_at else None,
                "model": (wf.config or {}).get("model"),
                "result": {
                    "train_acc": getattr(getattr(wf, "result", None), "summary", {}).get("train_acc") if getattr(wf, "result", None) else None,
                    "val_acc":   getattr(getattr(wf, "result", None), "summary", {}).get("val_acc") if getattr(wf, "result", None) else None,
                } if hasattr(wf, "result") else None,
                "steps": [_serialize_step(s) for s in steps],
            })
        return JsonResponse(data, safe=False)
    
class WorkflowPeekAPIView(View):
    """
    Verilen WF ID'nin kısa özeti:
    - dataset: id, name, file_path
    - preprocess: son step (varsa) ve processed_path bilgisi
    - config: model + hiperparametreler
    """
    def get(self, request, workflow_id):
        wf = get_object_or_404(Workflow.objects.select_related('dataset'), id=workflow_id)

        # Son preprocess step'i bul
        pre_step = wf.steps.filter(step_name='preprocess').order_by('-started_at').first()
        pre_info = None
        if pre_step:
            pre_info = {
                'status': pre_step.status,
                'has_processed_path': bool((pre_step.result or {}).get('processed_path')),
                'processed_path': (pre_step.result or {}).get('processed_path'),
                'completed_at': pre_step.completed_at.isoformat() if pre_step.completed_at else None
            }

        data = {
            'id': wf.id,
            'name': wf.name,
            'dataset': {
                'id': getattr(wf.dataset, 'id', None),
                'name': getattr(wf.dataset, 'name', None),
                'file_path': (wf.dataset.file.path if getattr(wf.dataset, 'file', None) else None),
            },
            'config': wf.config or {},
            'preprocess': pre_info
        }
        return JsonResponse(data)
    
