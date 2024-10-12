from django.contrib import admin
from .models import Board, Image, Category, History, Tab, Care_giver, Care_recipient, Image_positions

admin.site.register(Board)
admin.site.register(Category)
admin.site.register(Image)
admin.site.register(Tab)
admin.site.register(Care_giver)
admin.site.register(Care_recipient)
admin.site.register(Image_positions)
admin.site.register(History)
