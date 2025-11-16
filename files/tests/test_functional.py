from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from  selenium.webdriver.chrome.webdriver import WebDriver
from django.contrib.auth.models import User
from django.test import override_settings
import os


@override_settings(ALLOWED_HOSTS=['*'])
class FunctionalTest(StaticLiveServerTestCase):
    """
    Функциональные тесты для файлового менеджера
    """
    driver: WebDriver

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        driver_path = os.path.join(os.getcwd(), "chromedriver")
        cls.driver = webdriver.Chrome(driver_path)
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
        )
        self.client.login(username="testuser", password="password123")

        self.session = self.client.session
        self.session.save()

    def test_user_can_register_and_enter_on_main_page(self):
        """
        Пользователь регистрируется и попадает на главную страницу с файловым менеджером
        :return:
        """

    def test_user_can_create_folder(self):
        """
        Пользователь создает новую папку
        :return:
        """

    def test_user_can_upload_files(self):
        """
        Пользователь загружает файлы в облачный сервис через пользовательский интерфейс
        :return:
        """

    def test_user_can_download_file(self):
        """
        Пользователь скачивает файл из облачного сервиса
        :return:
        """

    def test_user_can_rename_object_via_modal(self):
        """
        Пользователь переименовывает файл или папку через модальное окно
        :return:
        """

    def test_user_can_delete_object(self):
        """
        Пользователь удаляет файл или папку(рекурсивно)
        :return:
        """

    def test_user_can_see_breadcrumbs_inside_folder(self):
        """
        Пользователь видит навигационную цепочку внутри папок
        :return:
        """

    def test_user_can_navigate_into_folder(self):
        """
        Пользователь может перемещаться между папками по нажатию по элементу пути
        навигационной цепочки
        :return:
        """

    def test_user_can_find_object_via_search_form_in_ui(self):
        """
        Пользователь может найти файл или папку через форму поиска
        :return:
        """