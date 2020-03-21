from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from .models import Comment, Reply


@receiver(post_save, sender=Comment)
def send_mail_to_author(sender, instance, created, **kwargs):

    if created:
        request = instance.request
        post = instance.target

        context = {
            'post': post,
        }
        subject = render_to_string('blog/mail/comment_notify_subject.txt', context, request)
        message = render_to_string('blog/mail/comment_notify_message.txt', context, request)
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [post.user.email]
        send_mail(subject, message, from_email, recipient_list)


@receiver(post_save, sender=Reply)
def send_mail_to_comment_user(sender, instance, created, **kwargs):

    if created:
        request = instance.request
        comment = instance.target
        post = comment.target

        context = {
            'post': post,
        }
        subject = render_to_string('blog/mail/reply_notify_subject.txt', context, request)
        message = render_to_string('blog/mail/reply_notify_message.txt', context, request)
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [comment.user.email]
        send_mail(subject, message, from_email, recipient_list)
