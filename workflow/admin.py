from django.contrib import admin
from .models import Workflow, WorkflowStep, Dataset

admin.site.register(Workflow)
admin.site.register(WorkflowStep)
admin.site.register(Dataset)