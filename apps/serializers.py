from django.contrib.auth.models import User, Group
from rest_framework import serializers
from .models import Care_recipient, Care_giver, Category, Image, Board, Tab, Image_positions, History, Codes


class CareRecipientSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="get_number_id", read_only=True)

    class Meta:
        model = Care_recipient
        fields = ['user', 'profile_pic', 'user_id']


class CaregiverSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="get_number_id", read_only=True)
    recipients = CareRecipientSerializer(many=True, read_only=True)

    class Meta:
        model = Care_giver
        fields = ['user', 'profile_pic', 'recipients', 'user_id']


class CategorySerializer(serializers.ModelSerializer):
    is_private = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'creator', 'is_private', 'display_name']

    def get_is_private(self, obj):
        return obj.is_private()

    def get_display_name(self, obj):
        return str(obj)


class ImageSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source="creator.username", read_only=True)

    class Meta:
        model = Image
        fields = ['id', 'label', 'image', 'category', 'public', 'creator', 'creator_name']


class BoardSerializer(serializers.ModelSerializer):
    access_users = CaregiverSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'name', 'creator', 'access_users', 'color']


class TabSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tab
        fields = ['id', 'name', 'straps_num', 'board', 'color']


class ImagePositionSerializer(serializers.ModelSerializer):
    image_label = serializers.CharField(source="image.label", read_only=True)

    class Meta:
        model = Image_positions
        fields = ['id', 'image', 'image_label', 'position_x', 'position_y', 'tab']


class HistorySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    board_name = serializers.CharField(source="board.name", read_only=True)

    class Meta:
        model = History
        fields = ['id', 'text', 'date', 'time', 'user', 'user_name', 'board', 'board_name']


class CodesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Codes
        fields = ['id', 'code', 'user', 'time']


class VerifyCodeSerializer(serializers.Serializer):
    code_check = serializers.CharField(max_length=10)


class PlaySoundSerializer(serializers.Serializer):
    input_data = serializers.CharField()
    board_id = serializers.IntegerField()


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role')
        user = User(**validated_data)
        user.set_password(validated_data['password'])  # Hash the password
        user.save()

        if role == 'cg_role':
            Care_giver.objects.get_or_create(user=user)
            # Add user to CAREGIVER group
            my_group, _ = Group.objects.get_or_create(name='CAREGIVER')
            my_group.user_set.add(user)
        elif role == 'cr_role':
            Care_recipient.objects.get_or_create(user=user)
            # Add user to RECIPIENT group
            my_group, _ = Group.objects.get_or_create(name='RECIPIENT')
            my_group.user_set.add(user)

        return user


# class FolderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Folder
#         fields = '__all__'
