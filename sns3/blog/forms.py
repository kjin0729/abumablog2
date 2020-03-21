from django import forms
from .models import Post, Comment, Reply
from django.contrib.auth.forms import (
    AuthenticationForm, UserCreationForm,
    PasswordChangeForm, PasswordResetForm,
    SetPasswordForm
)
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from .widgets import FileUploadableTextArea


User = get_user_model()

class PostSearchForm(forms.Form):

    key_word = forms.CharField(
        label='検索キーワード',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '投稿検索'}),
    )


class UserSearchForm(forms.Form):

    user_key_word = forms.CharField(
        label='検索キーワード',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ユーザー検索(名前で検索してください)'}),
    )

class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        exclude = ('likes',)
        widgets = {
            'text': FileUploadableTextArea,
        }


class PostCreateForm(forms.ModelForm):

    class Meta:
        model = Post
        exclude = ('created_at', 'user', 'likes')
        widgets = {
            'text': FileUploadableTextArea,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class PostUpdateForm(forms.ModelForm):

    class Meta:
        model = Post
        exclude = ('created_at', 'user', 'likes')
        widgets = {
            'text': FileUploadableTextArea,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class CommentCreateForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ('text',)
        widgets = {
            'text': FileUploadableTextArea(attrs={'class': 'form-control'}),
        }


class ReplyCreateForm(forms.ModelForm):

    class Meta:
        model = Reply
        fields = ('text',)
        widgets = {
            'text': FileUploadableTextArea(attrs={'class': 'form-control'}),
        }


class LoginForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label


class UserCreateForm(UserCreationForm):

    class Meta:
        model = User
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data['email']
        User.objects.filter(email=email, is_active=False).delete()
        return email


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('last_name', 'first_name', 'thumbnail')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class MyPasswordChangeForm(PasswordChangeForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class MyPasswordResetForm(PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class MySetPasswordForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class EmailChangeForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data['email']
        User.objects.filter(email=email, is_active=False).delete()
        return email


class FileUploadForm(forms.Form):
    file = forms.FileField()

    def save(self):
        upload_file = self.cleaned_data['file']
        file_name = default_storage.save(upload_file.name, upload_file)
        file_url = default_storage.url(file_name)
        return file_url
