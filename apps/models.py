from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
import datetime

# Create your models here.
class Care_recipient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return self.user.username

    def get_number_id(self):
        id = str(self.user.id)
        if len(id) < 6:
            while len(id) != 6:
                id = '0' + id
        return id

class Care_giver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    recipients = models.ManyToManyField(Care_recipient, null=True, blank=True)

    def __str__(self):
        return self.user.username

    def get_number_id(self):
        id = str(self.user.id)
        if len(id) < 6:
            while len(id) != 6:
                id = '0' + id
        return id

class Category(models.Model):
    name = models.CharField(max_length=100)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, default=0)

    def __str__(self):
        if (self.creator.is_staff):
            return self.name
        return self.name+' (личное)'

    def is_private(self):
        if (self.creator.is_staff):
            return False
        return True

class Image(models.Model):
    label = models.CharField(max_length=50, blank=False)
    image = models.ImageField(upload_to='library/')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    public = models.BooleanField(default=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.label

class Board(models.Model):
    name = models.CharField(max_length=100)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    access_users = models.ManyToManyField(Care_giver, null=True, blank=True)
    color = models.CharField(max_length=50, default='#cc4b48')

    def __str__(self):
        return self.name

class Tab(models.Model):
    name = models.CharField(max_length=50, null=True)
    straps_num = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    board = models.ForeignKey(Board, on_delete=models.CASCADE)
    color = models.CharField(max_length=50, default='#619451')

    def __str__(self):
        if self.name is not None:
            return self.name
        return " "

class Image_positions(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    position_x = models.CharField(max_length=50)
    position_y = models.CharField(max_length=50)
    tab = models.ForeignKey(Tab, on_delete=models.CASCADE)

class History(models.Model):
    text = models.CharField(max_length=250)
    date = models.DateField()
    time = models.TimeField(default=datetime.datetime.now().strftime("%H:%M:%S"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=False)
