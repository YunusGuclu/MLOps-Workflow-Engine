# workflow/urls.py
from django.urls import path
from . import views


app_name = 'workflow'

from django.views.generic import TemplateView

urlpatterns = [
    path('', views.WorkflowCreateView.as_view(), name='create'),
    path('workflows/', views.WorkflowListView.as_view(), name='list'),
    path('monitor/<int:workflow_id>/', views.MonitorView.as_view(), name='monitor'),
    path('api/metrics/<int:workflow_id>/', views.MetricsAPIView.as_view(), name='metrics'),
    path('api/status/<int:workflow_id>/',  views.WorkflowStatusAPIView.as_view(), name='status'),
    path('api/steps/<int:workflow_id>/', views.StepsAPIView.as_view(), name='steps'),
    path('api/result/<int:workflow_id>/', views.ResultAPIView.as_view(), name='result'),
    path('flower/',
        TemplateView.as_view(template_name='workflow/flower.html'),
        name='flower'
    ),
    path('queue/', views.QueueDashboardView.as_view(), name='queue'),
    path('api/queue/status/', views.QueueStatusAPIView.as_view(), name='queue-status'),
    path('api/queue/workflows/', views.QueueWorkflowsAPIView.as_view(), name='queue-workflows'),
    path('api/workflow/peek/<int:workflow_id>/', views.WorkflowPeekAPIView.as_view(), name='peek'),

]
