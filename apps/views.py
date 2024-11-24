import random
from datetime import datetime

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .application import play_sound
from .login import is_recipient, is_caregiver
from .models import Care_recipient, Care_giver, Codes, Board, Folder, Image, Tab, Image_positions, History
from .serializers import VerifyCodeSerializer, PlaySoundSerializer, BoardSerializer, \
    HistorySerializer, ImageSerializer, FolderSerializer, TabSerializer, \
    ImagePositionSerializer, FolderImageSerializer


class GenerateCodeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Generate a new verification code for the authenticated user",
        responses={
            201: openapi.Response(
                description="Code generated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_STRING),
                        'time': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def post(self, request):
        Codes.objects.filter(user=request.user).delete()

        code = ' '.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
        now = datetime.now().strftime("%H:%M:%S")

        code_lib, created = Codes.objects.get_or_create(code=code, user=request.user, defaults={'time': now})

        return Response({
            "code": code_lib.code,
            "time": code_lib.time,
            "message": "Code generated successfully"
        }, status=status.HTTP_201_CREATED)


class VerifyCodeView(APIView):
    @swagger_auto_schema(
        request_body=VerifyCodeSerializer,
        responses={
            200: openapi.Response(
                description="Code verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Invalid request data",
            404: "Code not found"
        }
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            code_check = serializer.validated_data.get('code_check')

            try:
                code = Codes.objects.get(code=code_check)
            except Codes.DoesNotExist:
                return Response({'success': False, 'message': "Code not found. Please try again."},
                                status=status.HTTP_404_NOT_FOUND)

            user = request.user
            if is_caregiver(user):
                caregiver = Care_giver.objects.get(user=user)
                recipient = Care_recipient.objects.get(user=code.user)
                caregiver.recipients.add(recipient)
            elif is_recipient(user):
                caregiver = Care_giver.objects.get(user=code.user)
                recipient = Care_recipient.objects.get(user=user)
                caregiver.recipients.add(recipient)
            else:
                return Response({'success': False, 'message': "User role not recognized."},
                                status=status.HTTP_400_BAD_REQUEST)

            return Response({'success': True, 'message': "Code verified successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlaySoundView(APIView):

    @swagger_auto_schema(
        query_serializer=PlaySoundSerializer(),
        responses={
            200: openapi.Response(
                description="Sound played successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'board': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: "Invalid request data",
            404: "Board not found"
        }
    )
    def get(self, request):
        serializer = PlaySoundSerializer(data=request.GET)

        if serializer.is_valid():
            input_data = serializer.validated_data.get('input_data')
            board_id = serializer.validated_data.get('board_id')

            try:
                board = Board.objects.get(id=board_id)
                board_serializer = BoardSerializer(board)
            except Board.DoesNotExist:
                return Response({'success': False, 'message': "Board not found."}, status=status.HTTP_404_NOT_FOUND)

            user = request.user
            if user.is_authenticated:
                history_data = {
                    'text': input_data,
                    'date': datetime.today(),
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'user': user.id,
                    'board': board.id
                }
                history_serializer = HistorySerializer(data=history_data)

                if history_serializer.is_valid():
                    history_serializer.save()
                else:
                    return Response(history_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            play_sound.playtext(input_data)
            return Response({
                'success': True,
                'message': "Sound played successfully.",
                'board': board_serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LibraryView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get library folders and images",
        responses={
            200: openapi.Response(
                description="Library data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'current_path': openapi.Schema(type=openapi.TYPE_STRING),
                        'folders': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                  items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'images': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'private_imgs': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                       items=openapi.Schema(type=openapi.TYPE_OBJECT))
                    }
                )
            )
        }
    )
    def get(self, request):
        folders = Folder.objects.all().order_by('name')
        public_folders = [cat for cat in folders if not cat.is_private()]
        private_folders = []

        if not request.user.is_staff:
            private_folders = list(Folder.objects.filter(creator=request.user).order_by('name'))

        folders = public_folders + private_folders
        images_data = {}

        for folder in folders:
            images_data[folder.name] = Image.objects.filter(folder=folder).values('image').distinct()[:1]

        private_images = Image.objects.filter(creator=request.user).values('image', 'label').distinct()

        response_data = {
            'current_path': request.path,
            'folders': FolderSerializer(folders, many=True).data,
            'images': images_data,
            'private_imgs': list(private_images),  # Convert to list if needed
        }
        return Response(response_data)

    # @swagger_auto_schema(
    #     request_body=ImageSerializer,
    #     responses={
    #         201: "Image uploaded successfully",
    #         400: "Invalid image data"
    #     }
    # )
    # def post(self, request):
    #     image_form = ImageSerializer(data=request.data)
    #     if image_form.is_valid():
    #         image = image_form.save(creator=request.user)
    #         return Response({"message": "Image uploaded successfully"}, status=201)
    #
    #     return Response(image_form.errors, status=400)


class BoardCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all boards for the authenticated user",
        responses={
            200: openapi.Response(
                description="Boards retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'boards': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                 items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'is_cr': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'is_cg': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            )
        }
    )
    def get(self, request):
        boards = Board.objects.filter(creator=request.user)
        serializer = BoardSerializer(boards, many=True)

        response_data = {
            'boards': serializer.data,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            201: "Board and default tab created successfully",
            400: "Board name is required",
            200: "Board already exists"
        }
    )
    def post(self, request):
        name = request.data.get('name')

        if not name:
            return Response({"error": "Board name is required."}, status=status.HTTP_400_BAD_REQUEST)

        board, created = Board.objects.get_or_create(name=name, creator=request.user)

        if created:
            Tab.objects.get_or_create(board=board, straps_num=5, name='Главная')
            return Response({"message": "Board and default tab created successfully."}, status=status.HTTP_201_CREATED)

        return Response({"message": "Board already exists."}, status=status.HTTP_200_OK)


folder_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'images': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                    'image': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        'folder': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'name': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        'is_cr': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        'is_cg': openapi.Schema(type=openapi.TYPE_BOOLEAN),
    }
)


class FolderImageView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get images for a specific folder",
        responses={
            200: folder_response,
            404: openapi.Response(description="folder not found")
        },
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="folder ID",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ]
    )
    def get(self, request, id):
        try:
            folder = Folder.objects.get(id=id)

            # images = Image.objects.filter(folder=folder).values('id', 'label', 'image').distinct()

            images = Image.objects.filter(folder=folder).distinct()

            serializer = ImageSerializer(images, many=True, context={'request': request})

            response_data = {
                'id': folder.id,
                'name': folder.name,
                'is_cr': is_recipient(request.user),
                'is_cg': is_caregiver(request.user),
                'images': serializer.data # Convert to list for JSON serialization
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Folder.DoesNotExist:
            return Response({'error': 'folder not found.'}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['folder_name', 'image'],
            properties={
                'folder_name': openapi.Schema(type=openapi.TYPE_STRING,
                                              description="The name of the folder."),
                'image': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY,
                                        description="Image file."),
                'label': openapi.Schema(type=openapi.TYPE_STRING, description="Optional label for the image."),
            }
        ),
        responses={
            201: "Image uploaded successfully and added to folder",
            400: "Invalid data",
        }

    )
    def post(self, request, id):
        image_data = request.FILES.get('image')  # Get the uploaded image
        label = request.data.get('label', '')  # Get the label

        # Check if both folder_name and image are provided
        if not image_data:
            return Response(
                {"error": "'image' field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not label:
            return Response(
                {"error": "'label' field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve the folder by its id
        try:
            folder = Folder.objects.get(id=id)
        except Folder.DoesNotExist:
            return Response(
                {"error": "Folder with the specified ID does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create and save the image under the folder
        try:
            image = Image.objects.create(
                folder=folder,
                image=image_data,  # Store the image file
                label=label,
                creator=request.user,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to upload image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Serialize the response
        serializer = ImageSerializer(image)

        response_message = {
            "message": "Image uploaded successfully.",
            "folder_id": folder.id,
            "image_id": image.id,
            "image_details": serializer.data
        }
        return Response(response_message, status=status.HTTP_201_CREATED)


class BoardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get detailed information about a board",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'tabs': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'is_cr': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'is_cg': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'tabs_img': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'folders': openapi.Schema(type=openapi.TYPE_ARRAY,
                                              items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'c_images': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'images': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'board_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            ),
            404: openapi.Response(description="Board not found")
        },
        manual_parameters=[
            openapi.Parameter(
                'board_id',
                openapi.IN_PATH,
                description="Board ID",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ]
    )
    def get(self, request, board_id):
        try:
            board = Board.objects.get(id=board_id)
        except Board.DoesNotExist:
            return Response({"error": "Board not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve public folders created by staff and private folders created by the user
        public_folders = Folder.objects.filter(creator__is_staff=True).order_by('name')
        private_folders = Folder.objects.filter(creator=request.user).order_by('name')

        # Combine the public and private folders
        folders = public_folders | private_folders

        # Fetch the images for each folder (distinction logic can be handled at the query level)
        c_images = {
            folder.id: ImageSerializer(
                Image.objects.filter(folder=folder).distinct()[:1], many=True
            ).data
            for folder in folders
        }

        # Retrieve all images in the combined folders
        images = Image.objects.filter(folder__in=folders)

        # Retrieve tabs for the board and associated image positions
        tabs = Tab.objects.filter(board=board).order_by('id')
        tabs_data = []

        for tab in tabs:
            # Use prefetch_related for Image_positions to optimize queries
            tab_positions = Image_positions.objects.filter(tab=tab).distinct()
            tabs_img = ImagePositionSerializer(tab_positions, many=True).data
            tabs_data.append({'tab': TabSerializer(tab).data, 'images': tabs_img})

        # Construct the response data
        response_data = {
            'tabs': TabSerializer(tabs, many=True).data,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
            'tabs_img': tabs_data,
            'folders': FolderSerializer(folders, many=True).data,
            'c_images': c_images,  # Now using folder IDs as keys
            'images': ImageSerializer(images, many=True).data,
            'board_id': board.id,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Create a new tab in a board",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'straps', 'color'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'straps': openapi.Schema(type=openapi.TYPE_INTEGER),
                'color': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            201: openapi.Response(description="Tab created successfully"),
            404: openapi.Response(description="Board not found"),
            400: openapi.Response(description="Missing required fields")
        }
    )
    def post(self, request, board_id):
        try:
            board = Board.objects.get(id=board_id)
        except Board.DoesNotExist:
            return Response({"error": "Board not found."}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name')
        straps_num = request.data.get('straps')
        color = request.data.get('color')

        if not all([name, straps_num, color]):
            return Response({"error": "Missing fields for new tab creation."}, status=status.HTTP_400_BAD_REQUEST)

        new_tab, created = Tab.objects.get_or_create(
            name=name,
            board=board,
            color=color,
            straps_num=straps_num
        )
        return Response({"message": "Tab created successfully.", "tab": TabSerializer(new_tab).data},
                        status=status.HTTP_201_CREATED)


class BoardFolderView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get folder and its images",
        manual_parameters=[
            openapi.Parameter(
                'input_data',
                openapi.IN_QUERY,
                description="folder ID",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'folder': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'folder_images': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                }
            ),
            404: openapi.Response(description="folder not found"),
            400: openapi.Response(description="folder ID is required")
        }
    )
    def get(self, request):
        folder_id = request.query_params.get("input_data")

        # Validate that folder ID is provided
        if not folder_id:
            return Response({"error": "folder ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            folder = Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist:
            return Response({"error": "folder not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all images related to the folder
        folder_images = Image.objects.filter(folder_id=folder_id)

        # Serialize the folder and images
        folder_data = FolderSerializer(folder).data
        folder_images_data = ImageSerializer(folder_images, many=True).data

        response_data = {
            'folder': folder_data,
            'folder_images': folder_images_data
        }

        return Response(response_data, status=status.HTTP_200_OK)


class BarCharsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this view

    @swagger_auto_schema(
        operation_description="Get word count data per hour for a specific date",
        manual_parameters=[
            openapi.Parameter(
                'bar_date',
                openapi.IN_QUERY,
                description="Date for bar chart data (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=True
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'bar': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_INTEGER),
                        description="Array of 24 integers representing word counts for each hour"
                    ),
                }
            ),
            400: openapi.Response(description="Invalid date format or missing date parameter")
        }
    )
    def get(self, request):
        # Retrieve and format the date from request parameters
        received_date = request.query_params.get('bar_date')
        if not received_date:
            return Response({"error": "Date parameter 'bar_date' is required"}, status=400)

        try:
            received_date = datetime.strptime(received_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Expected YYYY-MM-DD."}, status=400)

        # Query and filter data based on the date and user
        bar_data = History.objects.filter(date=received_date, user=request.user).values('text', 'time')
        bar = []

        for hour in range(0, 24):
            word_count = sum(
                len(d['text'].split()) for d in bar_data if d['time'].hour == hour
            )
            bar.append(word_count)

        return Response({'bar': bar}, status=200)


class ProgressView(APIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view

    @swagger_auto_schema(
        operation_description="Get user progress statistics",
        responses={
            200: openapi.Response(
                description="Progress data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'histories': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'is_recipient': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'board_names': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                      items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'board_representation': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                               items=openapi.Schema(type=openapi.TYPE_NUMBER))
                    }
                )
            )
        }
    )
    def get(self, request):
        # folders = folder.objects.values('id', 'name')
        histories = list(History.objects.filter(user=request.user.id).values('text', 'date', 'time'))[::-1]
        boards = Board.objects.filter(creator=request.user)

        boards_h = History.objects.filter(user=request.user).values('board', 'text')
        b = []  # List of board names
        rep = []  # List of representation percentages for each board

        for board in boards:
            count = 0
            b.append(board.name)
            for bh in boards_h:
                if board.id == bh['board']:
                    count += 1
            if len(boards_h) > 0:
                rep.append(count / len(boards_h) * 100)
            else:
                rep.append(0)

        data = {
            'histories': histories,
            'is_recipient': is_recipient(request.user),
            'board_names': b,
            'board_representation': rep,
        }

        return Response(data, status=200)


class FolderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new folder!",
        request_body=FolderSerializer,
        responses={
            201: "folder created successfully",
            400: "Invalid input"
        }
    )
    def post(self, request):
        folder_data = request.data
        serializer = FolderSerializer(data=folder_data)

        if serializer.is_valid():
            folder = serializer.save(creator=request.user)
            return Response({"message": "folder created successfully", "folder": serializer.data}, status=201)

        return Response(serializer.errors, status=400)
