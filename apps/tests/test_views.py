from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import datetime

from apps.models import (
    Care_recipient,
    Care_giver,
    Codes,
    Board,
    Category,
    Image,
    Tab,
    Image_positions,
    History
)


class APIEndpointTests(APITestCase):
    def setUp(self):
        # Create user groups
        self.recipient_group = Group.objects.create(name='RECIPIENT')
        self.caregiver_group = Group.objects.create(name='CAREGIVER')

        # Create test users
        self.recipient_user = User.objects.create_user(
            username='testrecipient',
            password='testpass123'
        )
        self.recipient_user.groups.add(self.recipient_group)
        self.care_recipient = Care_recipient.objects.create(user=self.recipient_user)

        self.caregiver_user = User.objects.create_user(
            username='testcaregiver',
            password='testpass123'
        )
        self.caregiver_user.groups.add(self.caregiver_group)
        self.care_giver = Care_giver.objects.create(user=self.caregiver_user)

        # Create test tokens
        self.recipient_token = Token.objects.create(user=self.recipient_user)
        self.caregiver_token = Token.objects.create(user=self.caregiver_user)

        # Create test board and related objects
        self.category = Category.objects.create(
            name='Test Category',
            creator=self.caregiver_user
        )

        self.board = Board.objects.create(
            name='Test Board',
            creator=self.caregiver_user
        )

        self.tab = Tab.objects.create(
            name='Test Tab',
            board=self.board,
            straps_num=5,
            color='#000000'
        )

        self.image = Image.objects.create(
            label='Test Image',
            image='test.jpg',
            category=self.category,
            creator=self.caregiver_user
        )

        # Create API client
        self.client = APIClient()

    def test_login_endpoint(self):
        """Test login functionality"""
        url = reverse('login')
        data = {
            'username': 'testrecipient',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_recipient_profile(self):
        """Test recipient profile endpoint"""
        url = reverse('recipient_profile')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.recipient_token.key}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_cr'])

    def test_caregiver_profile(self):
        """Test caregiver profile endpoint"""
        url = reverse('caregiver_profile')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('caregiver' in response.data)

    def test_generate_code(self):
        """Test code generation endpoint"""
        url = reverse('generate_code')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('code' in response.data)

    def test_verify_code(self):
        """Test code verification endpoint"""
        # First generate a code
        code = Codes.objects.create(
            code='123 456',
            user=self.caregiver_user,
            time=datetime.now().strftime("%H:%M:%S")
        )

        url = reverse('verify_code')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.recipient_token.key}')
        data = {'code_check': '123 456'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_library_view(self):
        """Test library endpoint"""
        url = reverse('library')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('categories' in response.data)

    def test_board_collection(self):
        """Test board collection endpoints"""
        url = reverse('my_boards')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')

        # Test GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('boards' in response.data)

        # Test POST
        data = {'name': 'New Test Board'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_category_image(self):
        """Test category image endpoint"""
        url = reverse('category_image', kwargs={'name': self.category.name, 'id': self.category.id})
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('images' in response.data)

    def test_play_sound(self):
        """Test play sound endpoint"""
        url = reverse('call_play_sound')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        data = {
            'input_data': 'test sound',
            'board_id': self.board.id
        }
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_progress_tracking(self):
        """Test progress tracking endpoint"""
        url = reverse('progress')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('histories' in response.data)

    def test_bar_charts(self):
        """Test bar charts endpoint"""
        url = reverse('bars')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        params = {'bar_date': datetime.now().strftime('%Y-%m-%d')}
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('bar' in response.data)

    def test_logout(self):
        """Test logout endpoint"""
        url = reverse('logout')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caregiver_token.key}')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def tearDown(self):
        """Clean up after tests"""
        User.objects.all().delete()
        Group.objects.all().delete()
        Board.objects.all().delete()
        Category.objects.all().delete()
        Image.objects.all().delete()
        Tab.objects.all().delete()
        Token.objects.all().delete()