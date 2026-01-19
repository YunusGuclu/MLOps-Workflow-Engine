# workflow/chain.py
from celery import chain
from celery.utils.log import get_task_logger
from .tasks import upload_task, preprocess_task, train_task

logger = get_task_logger(__name__)
class WorkflowChain:
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
        # Immutable signature (si) kullanıyoruz ki önceki task sonucu ek argüman olarak geçmesin
        self.sig = chain(
            upload_task.si(workflow_id),
            preprocess_task.si(workflow_id),
            train_task.si(workflow_id),
        )

    def delay(self):
        self._log_chain("delay() ile zincir başlatılıyor")
        return self.sig.delay()

    def apply_async(self, **kwargs):
        self._log_chain("apply_async() ile zincir başlatılıyor")
        return self.sig.apply_async(**kwargs)

    def pretty(self):
        return (
            "workflow.tasks.upload_task(args=(%s,), kwargs={})  ->\n"
            "workflow.tasks.preprocess_task(args=(%s,), kwargs={})  ->\n"
            "workflow.tasks.train_task(args=(%s,), kwargs={})"
        ) % (self.workflow_id, self.workflow_id, self.workflow_id)

    def _log_chain(self, prefix=""):
        msg = f"{prefix}\n<WorkflowChain workflow={self.workflow_id}>\n{self.pretty()}"
        logger.info(msg)
        print(msg)


def get_chain_for_workflow(workflow_id: int) -> WorkflowChain:
    wc = WorkflowChain(workflow_id)
    wc._log_chain("Zincir oluşturuldu")
    return wc

def run_workflow(workflow_id: int):
    """Tek satırda zinciri başlat, AsyncResult döndür."""
    wc = get_chain_for_workflow(workflow_id)
    return wc.delay()
