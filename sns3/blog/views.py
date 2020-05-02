from django.shortcuts import render, get_object_or_404, redirect, resolve_url
from django.contrib.sites.shortcuts import get_current_site
from django.views import generic
from .models import Post, Category, Comment, Reply
from django.http import Http404, JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.urls import reverse_lazy
from django.db.models import Q
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, loads, dumps
from .forms import (
PostSearchForm, CommentCreateForm, ReplyCreateForm,
LoginForm, UserCreateForm, UserUpdateForm, MyPasswordChangeForm,
MyPasswordResetForm, MySetPasswordForm, EmailChangeForm, PostCreateForm, AuthenticationForm,
FileUploadForm, UserSearchForm, PostUpdateForm
)
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
# Create your views here.


User = get_user_model()


class ArchiveListMixin:

    model = Post
    paginate_by = 12
    date_field = 'created_at'
    template_name ='blog/post_list.html'
    allow_empty = True
    make_object_list = True


class PostList(ArchiveListMixin, generic.ArchiveIndexView):

    def get_queryset(self):
        return super().get_queryset().select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['heading'] = '最近の投稿'
        return context


class PostDetail(generic.DetailView):

    model = Post

    def get_queryset(self):
        return super().get_queryset().prefetch_related('comment_set__reply_set')

    def get_object(self, queryset=None):
        post = super().get_object()
        if post.created_at <= timezone.now():
            return post
        raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class PostCreate(LoginRequiredMixin, generic.CreateView):
    model = Post
    form_class = PostCreateForm
    template_name = 'blog/post_create.html'

    def form_valid(self, form):
        user_pk = self.kwargs['pk']
        user = get_object_or_404(User, pk=user_pk)
        post = form.save(commit=False)
        post.user = user
        post.save()
        return redirect('blog:detail', pk=post.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = get_object_or_404(User, pk=self.kwargs['pk'])
        return context


class PostCategoryList(ArchiveListMixin, generic.ArchiveIndexView):

    def get_queryset(self):
        self.category = category = get_object_or_404(Category, pk=self.kwargs['pk'])
        return super().get_queryset().filter(category=category).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['heading'] = '[{}]カテゴリの投稿'.format(self.category.name)
        return context


class PostYearList(ArchiveListMixin, generic.YearArchiveView):

    def get_queryset(self):
        return super().get_queryset().select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['heading'] = '{}年の投稿'.format(self.kwargs['year'])
        return context


class PostMonthList(ArchiveListMixin, generic.MonthArchiveView):

    month_format = '%m'

    def get_queryset(self):
        return super().get_queryset().select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['heading'] = '{}年{}月の投稿'.format(self.kwargs['year'], self.kwargs['month'])
        return context


class PostSearchList(ArchiveListMixin, generic.ArchiveIndexView):

    def get_queryset(self):
        queryset = super().get_queryset()
        self.request.form = form = PostSearchForm(self.request.GET)
        form.is_valid()
        self.key_word = key_word = form.cleaned_data['key_word']
        if key_word:
            queryset = queryset.filter(Q(title__icontains=key_word) | Q(text__icontains=key_word))
        return queryset.select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['heading'] = '[{}]の検索結果'.format(self.key_word)
        return context


class CommentCreate(LoginRequiredMixin, generic.CreateView):
    model = Comment
    form_class = CommentCreateForm

    def form_valid(self, form):
        post_pk = self.kwargs['pk']
        post = get_object_or_404(Post, pk=post_pk)
        comment = form.save(commit=False)
        comment.user = self.request.user
        comment.target = post
        comment.request = self.request
        comment.save()
        return redirect('blog:detail', pk=post_pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post'] = get_object_or_404(Post, pk=self.kwargs['pk'])
        return context


class ReplyCreate(LoginRequiredMixin, generic.CreateView):
    model = Reply
    form_class = ReplyCreateForm
    template_name = 'blog/comment_form.html'

    def form_valid(self, form):
        comment_pk = self.kwargs['pk']
        comment = get_object_or_404(Comment, pk=comment_pk)
        reply = form.save(commit=False)
        reply.user = self.request.user
        reply.target = comment
        reply.request = self.request
        reply.save()
        return redirect('blog:detail', pk=comment.target.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comment_pk = self.kwargs['pk']
        comment = get_object_or_404(Comment, pk=comment_pk)
        context['post'] = comment.target
        return context


class Login(LoginView):
    form_class = LoginForm
    template_name = 'blog/login.html'


class Logout(LogoutView):
    template_name = 'blog/post_list.html'


class UserCreate(generic.CreateView):
    template_name = 'blog/user_create.html'
    form_class = UserCreateForm

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        current_site = get_current_site(self.request)
        domain = current_site.domain
        context = {
            'protocol': self.request.scheme,
            'domain': domain,
            'token': dumps(user.pk),
            'user': user,
        }

        subject = render_to_string('blog/mail/subject.txt', context)
        message = render_to_string('blog/mail/message.txt', context)

        user.email_user(subject, message)
        return redirect('blog:user_create_done')


class UserCreateDone(generic.TemplateView):
    template_name = 'blog/user_create_done.html'


class UserCreateComplete(generic.TemplateView):
    template_name = 'blog/user_create_complete.html'
    timeout_seconds = getattr(settings, 'ACTIVATION_TIMEOUT_SECONDS', 60*60*24)

    def get(self, request, **kwargs):
        token = kwargs.get('token')
        try:
            user_pk = loads(token, max_age=self.timeout_seconds)

        except SignatureExpired:
            return HttpResponseBadRequest()

        except BadSignature:
            return HttpResponseBadRequest()

        else:
            try:
                user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                return HttpResponseBadRequest()
            else:
                if not user.is_active:
                    user.is_active = True
                    user.save()
                    return super().get(request, **kwargs)

        return HttpResponseBadRequest()


class OnlyYouMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.pk == self.kwargs['pk'] or user.is_superuser


class DeleteUpdateMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        user = get_object_or_404(User, pk=post.user.pk)
        user.pk == post.user.pk or user.is_superuser

class UserDetail(OnlyYouMixin, generic.DetailView):
    model = User
    template_name = 'blog/user_detail.html'


class UserUpdate(OnlyYouMixin, generic.UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'blog/user_form.html'

    def get_success_url(self):
        return resolve_url('blog:user_detail', pk=self.kwargs['pk'])


class UserPostPublicDetail(generic.ListView):
    model = Post
    template_name = 'blog/user_post_public_detail.html'
    paginate_by = 12

    def get_queryset(self):
        user = get_object_or_404(User, pk=self.kwargs['pk'])
        return super().get_queryset().filter(user=user)


class UserPostPrivateDetail(OnlyYouMixin, generic.ListView):
    model = Post
    template_name = 'blog/user_post_private_detail.html'
    paginate_by = 12

    def get_queryset(self):
        user = get_object_or_404(User, pk=self.kwargs['pk'])
        return super().get_queryset().filter(user=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = get_object_or_404(User, pk=self.kwargs['pk'])
        return context


class PostUpdate(generic.UpdateView):
    model = Post
    form_class = PostUpdateForm
    template_name = 'blog/post_update.html'

    def get_success_url(self):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        return resolve_url('blog:user_post_private_detail', pk=post.user.pk)


class PostDelete(generic.DeleteView):
    model = Post
    form_class = PostCreateForm
    template_name = 'blog/post_delete.html'
    success_url = reverse_lazy('blog:list')


class PostLikeToggle(generic.RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        post_url = post.get_absolute_url()
        user = self.request.user
        if user.is_authenticated:
            if user in post.likes.all():
                post.likes.remove(user)
            else:
                post.likes.add(user)

        return post_url


class PostLikeAPIToggle(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk=None, format=None):
        post = get_object_or_404(Post, pk=pk)
        post_url = post.get_absolute_url()
        user = self.request.user
        updated = False
        if user.is_authenticated:
            if user in post.likes.all():
                liked = False
                post.likes.remove(user)
            else:
                liked = True
                post.likes.add(user)
            updated = True

        data = {
            'updated': updated,
            'liked': liked,
        }

        return Response(data)


class UserSearch(generic.ListView):
        model = User
        paginate_by = 10

        def get_queryset(self):
            queryset = super().get_queryset()
            form = UserSearchForm(self.request.GET)
            if form.is_valid():
                self.user_key_word = user_key_word = form.cleaned_data.get('user_key_word')
                if user_key_word:
                    queryset = queryset.filter(Q(first_name__icontains=user_key_word) | Q(last_name__icontains=user_key_word))

            return queryset


        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['heading'] = '[{}]の検索結果'.format(self.user_key_word)
            return context



class PasswordChange(PasswordChangeView):
    form_class = MyPasswordChangeForm
    success_url = reverse_lazy('blog:password_change_done')
    template_name = 'blog/password_change.html'


class PasswordChangeDone(PasswordChangeDoneView):
    template_name = 'blog/password_change_done.html'


class PasswordReset(PasswordResetView):
    subject_template_name = 'blog/mail/password_reset_subject.txt'
    email_template_name = 'blog/mail/password_reset_message.txt'
    template_name = 'blog/password_reset_form.html'
    form_class = MyPasswordResetForm
    success_url = reverse_lazy('blog:password_reset_done')


class PasswordResetDone(PasswordResetDoneView):
    template_name = 'blog/password_reset_done.html'


class PasswordResetConfirm(PasswordResetConfirmView):
    form_class = MySetPasswordForm
    success_url = reverse_lazy('blog:password_reset_complete')
    template_name = 'blog/password_reset_confirm.html'


class PasswordResetComplete(PasswordResetCompleteView):
    template_name = 'blog/password_reset_complete.html'


class EmailChange(LoginRequiredMixin, generic.FormView):
    template_name = 'blog/email_change_form.html'
    form_class = EmailChangeForm

    def form_valid(self, form):
        user = self.request.user
        new_email = form.cleaned_data['email']

        current_site = get_current_site(self.request)
        domain = current_site.domain
        context = {
            'protocol': 'https' if self.request.is_secure() else 'http',
            'domain': domain,
            'token': dumps(new_email),
            'user': user,
        }

        #from_email = settings.DEFAULT_FROM_EMAIL
        subject = render_to_string('blog/mail/email_change_subject.txt', context)
        message = render_to_string('blog/mail/email_change_message.txt', context)
        send_mail(subject, message, None, [new_email])

        return redirect('blog:email_change_done')


class EmailChangeDone(LoginRequiredMixin, generic.TemplateView):
    template_name = 'blog/email_change_done.html'


class EmailChangeComplete(LoginRequiredMixin, generic.TemplateView):
    template_name = 'blog/email_change_complete.html'
    timeout_seconds = getattr(settings, 'ACTIVATION_TIMEOUT_SECONDS', 60*60*24)

    def get(self, request, **kwargs):
        token = kwargs.get('token')
        try:
            new_email = loads(token, max_age=self.timeout_seconds)

        except SignatureExpired:
            return HttpResponseBadRequest()

        except BadSignature:
            return HttpResponseBadRequest()

        else:
            User.objects.filter(email=new_email, is_active=False).delete()
            request.user.email = new_email
            request.user.save()
            return super().get(request, **kwargs)


def upload(request):
    form = FileUploadForm(file=request.FILES)
    if form.is_valid():
        path = form.save()
        url = '{0}://{1}{2}'.format(
            request.scheme,
            request.get_host(),
            path,
        )
        return JsonResponse({'url': url})
    return HttpResponseBadRequest()
