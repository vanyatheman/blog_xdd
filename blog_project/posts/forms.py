from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')

    def clean_text(self):
        data = self.cleaned_data['text']
        if not data:
            raise forms.ValidationError('заполните текст поста')
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
