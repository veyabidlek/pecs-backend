from django import forms
from django.contrib.auth.models import User
from . import models
import random
import string


class ImageForm(forms.ModelForm):
    class Meta:
        model = models.Image
        fields = ['label', 'image', 'public']

    # def __init__(self, *args, **kwargs):
    #     print("id", id)
    #     super().__init__(*args, **kwargs)
    #     self.fields['category'].queryset = models.Category.objects.filter(creator=1)


class FolderForm(forms.ModelForm):
    class Meta:
        model = models.Category
        fields = ['name']


class AddForm(forms.Form):
    image_id = forms.IntegerField()
    board = forms.ModelChoiceField(queryset=models.Board.objects.all(), empty_label="Выберите доску")
    tab = forms.ModelChoiceField(queryset=models.Tab.objects.all(), empty_label="Выберите вкладку")


class SignupForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password', 'email']
        widgets = {
            'password': forms.PasswordInput()
        }
