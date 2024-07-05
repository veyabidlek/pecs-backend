from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from . import forms, models
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .application import play_sound
from django.contrib.auth import authenticate, login, logout
import datetime

def call_play_sound(req):
    today = datetime.date.today()
    now = datetime.datetime.now().strftime("%H:%M:%S")
    if req.method == 'GET':
        # write_data.py write_csv()Call the method.
        #Of the data sent by ajax"input_data"To get by specifying.
        # voice = models.Board.objects.filter(name="PECS Board").values('voice_choice')
        # voice = voice[0]['voice_choice']
        text = req.GET.get("input_data")
        print(text)
        user = req.user
        # if user is not None:
        #     history = models.History(text=text, date=today, time=now, user=user)
        #     history.save()
        play_sound.playtext(text)
        return HttpResponse()

# Create your views here.
def index_view(request):
    dict = {'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user), }
    return render(request, 'index.html', dict)

def recipient_profile_view(request):
    dict = {'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user), }
    return render(request, 'recipient_profile_page.html', dict)

def caregiver_profile_view(request):
    dict = {'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user), }
    return render(request, 'caregiver_profile_page.html', dict)

def login_user_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if is_recipient(user):
                return redirect('recipient_profile')
            elif is_caregiver(user):
                return redirect('caregiver_profile')
        else:
            messages.success(request, ("Неправильный логин или пароль! Попробуйте снова."))
    return render(request, 'login_page.html', {})

def logout_user_view(request):
    logout(request)
    return redirect('home')

def signup_user_view(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        form = forms.SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.set_password(user.password)
            user.save()
            if role == 'cg_role':
                cg = models.Care_giver.objects.get_or_create(user=user)
                my_group = Group.objects.get_or_create(name='CAREGIVER')
                my_group[0].user_set.add(user)
            elif role == 'cr_role':
                cr = models.Care_recipient.objects.get_or_create(user=user)
                my_group = Group.objects.get_or_create(name='RECIPIENT')
                my_group[0].user_set.add(user)
            return redirect('login')
        else:
            messages.success(request, ("Такое имя пользователя уже существует. Попробуйте снова."))
    else:
        form = forms.SignupForm()
    dict = {'signupForm': form}
    return render(request, 'signup_page.html', dict)

def library_view(request):
    folderForm = forms.FolderForm()
    imageForm = forms.ImageForm()
    public_categories = []
    private_categories = []
    categories = models.Category.objects.all().order_by('name')
    for category in categories:
        if not category.is_private():
            public_categories.append(category)
    if not request.user.is_staff:
        private_categories = list(models.Category.objects.filter(creator=request.user.id).order_by('name'))
    categories = public_categories+private_categories
    images = {}
    for category in categories:
        images[category] = models.Image.objects.filter(category=category).values('image').distinct()[:1]
    private_images = models.Image.objects.filter(creator=request.user.id).values('image', 'label').distinct()
    dict = {'current_path': request.path,
            'categories': categories,
            'images': images,
            'imageForm': imageForm,
            'folderForm': folderForm,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
            'private_imgs': private_images,
            }
    if request.method == 'POST':
        imageForm = forms.ImageForm(request.POST, request.FILES, user=request.user)
        folderForm = forms.FolderForm(request.POST)
        if imageForm.is_valid():
            print("Imageeeeeeee")
            image = imageForm.save(commit=False)
            image.creator = request.user
            if not image.creator.is_staff:
                image.public = False
            image.save()
        if folderForm.is_valid():
            folder = folderForm.save(commit=False)
            folder.creator = request.user
            folder.save()
        return HttpResponseRedirect('library')
    return render(request, 'library.html', dict)

def category_image(request, name, id):
    addimageForm = forms.AddForm()
    category = models.Category.objects.get(id=id)
    images = models.Image.objects.filter(category=category).values('id', 'label', 'image').distinct()
    dict = {'images': images,
            'addimageForm': addimageForm,
            'category': category,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
            }
    if request.method == 'POST':
        addimageForm = forms.AddForm(request.POST)
        if addimageForm.is_valid():
            image_id = request.POST.get('image_id')
            tab_id = request.POST.get('tab')
            image = models.Image.objects.get(id=image_id)
            tab = models.Tab.objects.get(id=tab_id)
            pos=models.Image_positions.objects.get_or_create(tab=tab, image=image, position_x='0', position_y='0')
        return HttpResponseRedirect(str(id))
    return render(request, 'category_images.html', dict)

def board_collection_view(request):
    boards = models.Board.objects.filter(creator=request.user.id)
    dict = {'boards': boards,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
            }
    if request.method == 'POST':
        name = request.POST.get('name')
        board = models.Board.objects.get_or_create(name=name, creator=request.user)
        tab = models.Tab.objects.get_or_create(board=board[0], straps_num=5, name='Главная')
    return render(request, 'board_collection.html', dict)

def board_view(request, id):
    board = models.Board.objects.get(id=id)

    public_categories = []
    private_categories = []
    categories = models.Category.objects.all().order_by('name')
    for category in categories:
        if not category.is_private():
            public_categories.append(category)
    if not request.user.is_staff:
        private_categories = list(models.Category.objects.filter(creator=request.user.id).order_by('name'))
    categories = public_categories + private_categories
    c_images = {}
    images = []
    for category in categories:
        c_images[category] = models.Image.objects.filter(category=category).values('image').distinct()[:1]
        images += models.Image.objects.filter(category=category)

    if request.method == 'POST':
        name = request.POST.get('name')
        straps_num = request.POST.get('straps')
        color = request.POST.get('color')
        # print("122COLOR ", color)
        new_tab = models.Tab.objects.get_or_create(name=name, board=board, color=color, straps_num=straps_num)
    tabs = models.Tab.objects.filter(board=id).order_by('id')
    print(images)
    t_i = []
    for tab in tabs:
        tabs_img = list(models.Image_positions.objects.filter(tab=tab.id).distinct())
        t_i.append(tabs_img)

    dict = {'tabs': tabs,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
            'tabs_img': tabs_img,
            't_imgs': t_i,
            'current_path': request.path,
            'categories': categories,
            'c_images': c_images,
            'images': images,
            }
    return render(request, 'board.html', dict)

def is_recipient(user):
    return user.groups.filter(name='RECIPIENT').exists()
def is_caregiver(user):
    return user.groups.filter(name='CAREGIVER').exists()

