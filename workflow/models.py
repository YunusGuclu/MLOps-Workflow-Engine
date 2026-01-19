# workflow/models.py
from django.db import models

class Dataset(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='datasets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Workflow(models.Model):
    STATUS_CHOICES = [
        ('PENDING','Beklemede'),
        ('PREPROCESSING','Önişleme'),
        ('TRAINING','Eğitim'),
        ('COMPLETED','Tamamlandı'),
        ('FAILED','Hata'),
    ]
    name = models.CharField(max_length=255)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    config = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                               default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Workflow {self.id}'


class TrainingMetric(models.Model):
    workflow = models.ForeignKey(Workflow, related_name='metrics', 
                                 on_delete=models.CASCADE)
    epoch = models.IntegerField()
    metrics = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

class TrainingResult(models.Model):
    workflow = models.OneToOneField(Workflow, related_name='result', 
                                    on_delete=models.CASCADE)
    model_file = models.FileField(upload_to='models/')
    summary = models.JSONField()


class WorkflowStep(models.Model):
    workflow = models.ForeignKey(Workflow, related_name='steps',
                                  on_delete=models.CASCADE)
    step_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, 
                              choices=Workflow.STATUS_CHOICES, default='PENDING')
    params = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)
    task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Celery TaskResult.task_id ile ilişki"
   )

