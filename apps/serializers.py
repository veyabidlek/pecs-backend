from urllib.parse import quote

from django.contrib.auth.models import User, Group
from rest_framework import serializers

from .models import Care_recipient, Care_giver, Image, Board, Tab, Image_positions, History, Codes, Folder


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


class FolderSerializer(serializers.ModelSerializer):
    is_private = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ['id', 'name', 'creator', 'is_private', 'display_name']

    def get_is_private(self, obj):
        return obj.is_private()

    def get_display_name(self, obj):
        return str(obj)


# class FolderImageSerializer(serializers.ModelSerializer):
#     creator_name = serializers.CharField(source="creator.username", read_only=True)
#     image_url = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Image
#         fields = ['id', 'label', 'creator_name', 'image_url']

    # def get_image_url(self, obj):
    #     try:
    #         if obj.image:
    #             r2_base_url = "https://pub-f6fd6da427b441459aff60f0c2f6b9e3.r2.dev/"
    #             return f"{r2_base_url}{obj.image.name}"  # Use the file's storage path
    #         return None
    #     except Exception as e:
    #         print(f"Error getting image URL: {e}")
    #         return None


class ImageSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source="creator.username", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'label', 'folder', 'public', 'creator_id', 'creator_name', 'image_url']

    def get_image_url(self, obj):
        try:
            if obj.image:
                r2_base_url = "https://pub-f6fd6da427b441459aff60f0c2f6b9e3.r2.dev/"
                encoded_image_name = quote(obj.image.name)
                return f"{r2_base_url}{encoded_image_name}"
            return None
        except Exception as e:
            print(f"Error getting image URL: {e}")
            return None


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
    role = serializers.CharField(max_length=50, required=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=30, required=True)
    last_name = serializers.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'role']

    def validate(self, attrs):
        role = attrs.get('role')
        if role not in ['cg_role', 'cr_role']:
            raise serializers.ValidationError(
                {"role": "Invalid role specified. Use 'cg_role' for caregiver or 'cr_role' for care recipient."}
            )
        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role')
        user = User(**validated_data)
        user.set_password(validated_data['password'])  # Hash the password
        user.save()

        # Add role-specific logic after validation
        if role == 'cg_role':
            Care_giver.objects.get_or_create(user=user)
            my_group, _ = Group.objects.get_or_create(name='CAREGIVER')
            my_group.user_set.add(user)
        elif role == 'cr_role':
            Care_recipient.objects.get_or_create(user=user)
            my_group, _ = Group.objects.get_or_create(name='RECIPIENT')
            my_group.user_set.add(user)

        return user

#
# from apps.models import Care_recipient
# from django.contrib.auth.models import User

# user = User.objects.get(username='your_username')  # replace 'your_username' with the actual username
# try:
#     care_recipient = Care_recipient.objects.get(user=user)
#     print(care_recipient)
# except Care_recipient.DoesNotExist:
#     print("Care_recipient does not exist for this user.")
