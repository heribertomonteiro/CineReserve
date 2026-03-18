from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from cinema.models import Ticket

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 5},
)
def send_ticket_confirmation_email(self, ticket_id: int) -> None:
    ticket = (
        Ticket.objects
        .select_related("user", "session", "session__movie", "seat")
        .get(pk=ticket_id)
    )

    subject = "Confirmacao do ingresso"
    message = (
        f"Seu ingresso foi confirmado.\n"
        f"Filme: {ticket.session.movie.title}\n"
        f"Sessao: {ticket.session.starts_at}\n"
        f"Assento: {ticket.seat.label}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.user.email],
        fail_silently=False,
    )