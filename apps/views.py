from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from . import forms, models
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .application import play_sound, verification
from django.contrib.auth import authenticate, login, logout
import datetime
from auth_token import utils
from django.core.serializers.json import DjangoJSONEncoder
import json
import random

def generate_code(request):

    codes = models.Codes.objects.filter(user=request.user.id)
    codes.delete()
    code = ' '.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
    now = datetime.datetime.now().strftime("%H:%M:%S")
    code_lib = models.Codes.objects.get_or_create(code=code, user=request.user, time=now)
    return render(request, 'generate_code.html', {'code': code})

def verify_code(request, code_check):
    try:
        code = models.Codes.objects.get(code=code_check)
    except models.Codes.DoesNotExist:
        code = None

    if code is not None:
        if is_caregiver(request.user):
            caregiver = models.Care_giver.objects.get(user=request.user.id)
            recipient = models.Care_recipient.objects.get(user=code.user.id)
            caregiver.recipients.add(recipient)
        if is_recipient(request.user):
            caregiver = models.Care_giver.objects.get(user=code.user.id)
            recipient = models.Care_recipient.objects.get(user=request.user.id)
            caregiver.recipients.add(recipient)
    else:
        messages.success(request, ("Ничего не найдено. Попробуйте снова"))
    return
def call_play_sound(req):
    today = datetime.date.today()
    now = datetime.datetime.now().strftime("%H:%M:%S")
    if req.method == 'GET':
        # write_data.py write_csv()Call the method.
        #Of the data sent by ajax"input_data"To get by specifying.
        # voice = models.Board.objects.filter(name="PECS Board").values('voice_choice')
        # voice = voice[0]['voice_choice']
        text = req.GET.get("input_data")
        board_id = req.GET.get("board_id")
        board = models.Board.objects.get(id=board_id)
        print(text)
        user = req.user
        if user is not None:
            history = models.History(text=text, date=today, time=now, user=user, board=board)
            history.save()
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
                cg, cg_created = models.Care_giver.objects.get_or_create(user=user)
                my_group = Group.objects.get_or_create(name='CAREGIVER')
                my_group[0].user_set.add(user)
            elif role == 'cr_role':
                cr, cr_created = models.Care_recipient.objects.get_or_create(user=user)
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
        imageForm = forms.ImageForm(request.POST, request.FILES)
        folderForm = forms.FolderForm(request.POST)
        if imageForm.is_valid():
            image = imageForm.save(commit=False)
            image.creator = request.user
            image.category = models.Category.objects.get(id=request.POST.get('category'))
            print(image.category)

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

    # if request.method == 'GET':
    #     text = request.GET.get("input_data")
    #     print("BOARD TEXT", text)

    dict = {'tabs': tabs,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
            'tabs_img': tabs_img,
            't_imgs': t_i,
            'current_path': request.path,
            'categories': categories,
            'c_images': c_images,
            'images': images,
            'board_id': id,
            }
    return render(request, 'board.html', dict)

def board_category_view(request):
    if request.method == 'GET':
        id = request.GET.get("input_data")
        category = models.Category.objects.get(id=id)
        category_imgs = models.Image.objects.filter(category_id=id)

        dict = {'category': category,
                'category_imgs': category_imgs,}
    return render(request, 'board_category.html', dict)

def caregiver_profile_view(request):
    try:
        caregiver = models.Care_giver.objects.get(user=request.user)
        recipients = caregiver.recipients.all()
    except models.Care_giver.DoesNotExist:
        recipients = None

    if request.method == 'POST':
        d1 = str(request.POST.get('d1'))
        d2 = str(request.POST.get('d2'))
        d3 = str(request.POST.get('d3'))
        d4 = str(request.POST.get('d4'))
        d5 = str(request.POST.get('d5'))
        d6 = str(request.POST.get('d6'))

        code_check = d1 + d2 + d3 +" "+ d4 + d5 + d6
        print("check", code_check)
        verify_code(request, code_check)
    dict = {'caregiver': caregiver,
            'is_cg': True,
            'recipients': recipients,
            }
    return render(request, 'caregiver_profile_page.html', dict)
def recipient_profile_view(request):
    recipient = models.Care_recipient.objects.get(user=request.user)
    try:
        caregivers = models.Care_giver.objects.filter(recipients=recipient)
    except models.Care_giver.DoesNotExist:
        caregivers = None
    if request.method == 'POST':
        d1 = str(request.POST.get('d1'))
        d2 = str(request.POST.get('d2'))
        d3 = str(request.POST.get('d3'))
        d4 = str(request.POST.get('d4'))
        d5 = str(request.POST.get('d5'))
        d6 = str(request.POST.get('d6'))

        code_check = d1 + d2 + d3 +" "+ d4 + d5 + d6
        print("check", code_check)
        verify_code(request, code_check)

    dict = {'recipient': recipient,
            'is_cr': True,
            'caregivers': caregivers,
            }
    return render(request, 'recipient_profile_page.html', dict)
def profile_view(request):
    if is_recipient(request.user):
        return redirect('recipient_profile')
    elif is_caregiver(request.user):
        return redirect('caregiver_profile')

def recipient_profile_caregiver_view(request):
    # code = generate_code(request)
    recipient = models.Care_recipient.objects.get(user=request.user.id)
    try:
        caregivers = models.Care_giver.objects.filter(recipients=recipient)
    except models.Care_giver.DoesNotExist:
        caregivers = None
    dict = {'caregivers': caregivers}
    return render(request, 'recipient_profile_caregiver.html', dict)

def caregiver_recipient_view(request):
    # code = generate_code(request)
    try:
        caregiver = models.Care_giver.objects.get(user=request.user.id)
        recipients = caregiver.recipients
    except models.Care_giver.DoesNotExist:
        recipients = None
    dict = {
            'recipients': recipients}
    return render(request, 'caregiver_recipients.html', dict)

def bar_chars(request):
    if request.method == 'GET':
        received_data = request.GET.get('bar_date')
        bar_data = models.History.objects.filter(date=received_data, user=request.user).values('text', 'time')
        print(received_data)

        bar = []
        for i in range (0, 24):
            n=0
            if len(bar_data) != 0:
                for d in bar_data:
                    if d['time'].hour == i:
                        text = d['text'].split()
                        n += len(text)
            bar.append(n)
    return render(request, 'progress_tracking.html', {'bar': bar})
def progress(request):
    categories = models.Category.objects.values('id', 'name')
    histories = list(models.History.objects.filter(user=request.user.id).values('text', 'date', 'time'))[::-1]
    boards = models.Board.objects.filter(creator=request.user)
    print("B", boards)
    boards_h = models.History.objects.filter(user=request.user).values('board', 'text')
    print("BH", boards_h)
    b=[]
    rep=[]
    for board in boards:
        count = 0
        b.append(board.name)
        for bh in boards_h:
            if board.id == bh['board']:
                count += 1
        rep.append(count/len(boards_h)*100)
    print("rep", b)
    # num_img = []
    # used_img = []
    # tab_idx = set()
    # tab_dic = {}
    # tabs = models.Tab.objects.values('images')
    # val = []
    # name = []
    # for t in tabs:
    #     tab_idx.add(t['images'])
    # for j in tab_idx:
    #     cat = models.Image.objects.filter(id=j).values('category')
    #     tab_dic[j] = cat[0]['category']
    # for i in categories:
    #     image_num = len(models.Image.objects.filter(category = i['id']))
    #     name.append(i['name'])
    #     num_img.append(image_num)
    #     used_img.append(len(list(filter(lambda k: float(tab_dic[k]) == i['id'], tab_dic))))
    # for i in range (0, len(used_img)):
    #     if num_img[i] != 0:
    #         val.append((used_img[i], num_img[i], name[i], int(round(used_img[i]/num_img[i]*100, 0))))
    #     else:
    #         val.append((used_img[i], num_img[i], name[i], 0))
    dict={
        # 'val': val,
        # 'name': name,
        'histories': histories,
        'is_cr': is_recipient(request.user),
        'rep': rep,
        'boards': (b),
        }
    return render(request, 'progress_tracking.html', dict)

def is_recipient(user):
    return user.groups.filter(name='RECIPIENT').exists()
def is_caregiver(user):
    return user.groups.filter(name='CAREGIVER').exists()

