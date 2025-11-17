import boto3
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import WebDriver
from django.contrib.auth.models import User
from django.test import override_settings
from urllib.parse import quote
from moto import mock_aws
from webdriver_manager.chrome import ChromeDriverManager
import os
from time import sleep


@override_settings(ALLOWED_HOSTS=['*'])
class FunctionalTest(StaticLiveServerTestCase):
    """Функциональные тесты для файлового менеджера"""
    driver: WebDriver

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        service = ChromeService(ChromeDriverManager().install())

        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        cls.driver = webdriver.Chrome(service=service, options=options)
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.mock = mock_aws()
        self.mock.start()

        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            id=1

        )
        self.client.login(username="testuser", password="password123")

        self.session = self.client.session
        self.session.save()

        self.s3_client = boto3.client('s3', region_name='us-east-1')

        try:
            self.s3_client.create_bucket(Bucket='user-files')
        except Exception:
            pass

        self.prefix = f"user-{self.user.id}-files/"
        self.s3_client.put_object(Bucket='user-files', Key=f'{self.prefix}docs/', Body=b'')
        self.s3_client.put_object(Bucket='user-files', Key=f'{self.prefix}docs/projects/', Body=b'')
        self.s3_client.put_object(Bucket='user-files', Key=f'{self.prefix}docs/projects/file.txt', Body=b'content')
        self.s3_client.put_object(Bucket='user-files', Key=f'{self.prefix}file.txt', Body=b'content')

        print("SESSION KEY:", self.session.session_key)

    def tearDown(self):
        self.mock.stop()

    def login_browser(self):
        """Добавляет сессию в браузер"""
        session_id = self.client.session.session_key
        self.driver.get(f"{self.live_server_url}/")

        self.driver.add_cookie({
            'name': 'sessionid',
            'value': session_id,
            'path': '/'
        })
        self.driver.refresh()

        WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "h2"), "Файлы")
        )

    def test_user_can_register_and_enter_on_main_page(self):
        """Пользователь регистрируется и попадает на главную страницу с файловым менеджером"""
        driver = self.driver
        url = f"{self.live_server_url}/users/register/"

        driver.get(url)

        print("Current URL:", driver.current_url)
        print("Page title:", driver.title)

        driver.find_element(By.NAME, 'username').send_keys('newuser')
        driver.find_element(By.NAME, 'email').send_keys("newuser@example.com")
        driver.find_element(By.NAME, 'password1').send_keys('!COmplexpass123')
        driver.find_element(By.NAME, 'password2').send_keys('!COmplexpass123')

        driver.find_element(By.XPATH, '//button[@type="submit"]').click()

        WebDriverWait(driver, 10).until(EC.url_contains('/files/manager/'))
        WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.TAG_NAME, 'h2'), 'Файлы'))

        h2_text = driver.find_element(By.TAG_NAME, 'h2').text
        self.assertEqual(h2_text, 'Файлы')

    def test_user_can_create_folder(self):
        """Пользователь создает новую папку"""
        driver = self.driver
        url = f"{self.live_server_url}/files/manager/"

        driver.get(url)
        self.login_browser()

        create_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "showCreateForm")))
        create_btn.click()

        folder_input = driver.find_element(By.NAME, 'folder_name')
        folder_input.send_keys('Новая папка')

        submit_btn = driver.find_element(By.CSS_SELECTOR, '#createFolderForm button[type = "submit"]')
        submit_btn.click()

        sleep(1)
        driver.get(f"{self.live_server_url}/files/manager/")

        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//h5[text()='Новая папка']")))

        titles = [el.text for el in driver.find_elements(By.XPATH, "//h5[text()='Новая папка']")]
        self.assertIn("Новая папка", titles)

    def test_user_can_upload_files(self):
        """Пользователь загружает файлы в облачный сервис через пользовательский интерфейс"""
        driver = self.driver
        url = f"{self.live_server_url}/files/manager/"
        driver.get(url)
        self.login_browser()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card"))
        )

        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "files"))
        )

        file_path = os.path.join(os.getcwd(), 'test_files', 'sample.txt')
        assert os.path.exists(file_path), f"Файл не найден: {file_path}"

        file_input.send_keys(file_path)

        upload_btn = driver.find_element(By.ID, 'uploadBtn')
        upload_btn.click()

        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.XPATH, "//h5[text()='sample.txt']"), "sample.txt")
        )

        titles = [el.text for el in driver.find_elements(By.XPATH, "//h5[text()='sample.txt']")]
        self.assertIn("sample.txt", titles)

    def test_user_can_download_file(self):
        """Пользователь скачивает файл из облачного сервиса"""
        driver = self.driver
        driver.get(f"{self.live_server_url}/files/manager/")
        self.login_browser()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'card')))

        btn_download = driver.find_element(By.ID, 'btn-download')
        self.assertTrue(btn_download.is_displayed())

        main_window = driver.current_window_handle

        btn_download.click()

        try:
            WebDriverWait(driver, 10).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            self.fail(f"alert при скачивании {alert.text}")
        except:
            pass

    def test_user_can_rename_object_via_modal(self):
        """Пользователь переименовывает файл или папку через модальное окно"""
        driver = self.driver
        driver.get(f"{self.live_server_url}/files/manager/")
        self.login_browser()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'card')))

        driver.find_element(By.ID, 'btn-dropdown').click()
        rename_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'btn-rename-dropdown')))
        rename_btn.click()

        modal = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'renameModal')))

        new_name_input = modal.find_element(By.ID, 'newName')
        new_name_input.send_keys("renamed.pdf")

        save_btn = modal.find_element(By.ID, 'saveBtn')
        save_btn.click()

        WebDriverWait(driver, 10).until(EC.invisibility_of_element_located(modal))

        WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.CLASS_NAME, 'card-title'), 'renamed.pdf'))

        card_titles = [el for el in driver.find_elements(By.CLASS_NAME, 'card-title')]
        self.assertIn("renamed.pdf", card_titles)

    def test_user_can_delete_object(self):
        """Пользователь удаляет файл или папку(рекурсивно)"""
        driver = self.driver
        driver.get(f"{self.live_server_url}/files/manager/")
        self.login_browser()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'card')))

        driver.find_element(By.ID, 'btn-dropdown').click()
        delete_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'delete-submit')))
        delete_btn.click()

        WebDriverWait(driver, 10).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()

        try:
            WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, '//h5[text()="report.pdf"]')))

        except:
            driver.refresh()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

        card_titles = [el.text for el in driver.find_elements(By.CLASS_NAME, "card-title")]
        self.assertNotIn("report.pdf", card_titles)

    def test_user_can_see_breadcrumbs_inside_folder(self):
        """Пользователь видит навигационную цепочку внутри папок"""
        driver = self.driver
        url = f"{self.live_server_url}/files/manager/?path={quote(f'{self.prefix}docs/projects/')}"

        driver.get(url)
        self.login_browser()

        breadcrumbs = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'breadcrumb')))

        items = breadcrumbs.find_elements(By.CLASS_NAME, "breadcrumb-item")
        texts = [item.text for item in items]

        expected_parts = ['docs', 'projects']

        visible_texts = [text for text in texts if text.strip() and text != "Файлы"]

        self.assertEqual(expected_parts, visible_texts)

    def test_user_can_navigate_into_folder(self):
        """Пользователь может перемещаться между папками по нажатию по элементу пути навигационной цепочки"""
        driver = self.driver
        url = f"{self.live_server_url}/files/manager/?path=user-1-files%2Fdocs%2Fprojects%2F"

        driver.get(url)
        self.login_browser()

        breadcrumbs = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'breadcrumb')))

        doc_item = None
        for item in breadcrumbs.find_elements(By.CLASS_NAME, "breadcrumb-item"):
            if "docs" in item.text:
                link = item.find_element(By.TAG_NAME, "a")
                doc_item = link
                break

        self.assertIsNotNone(doc_item)

        doc_item.click()

        WebDriverWait(driver, 10).until(
            lambda d: "path=user-1-files%2Fdocs%2F" in d.current_url
        )
        current_url = driver.current_url
        self.assertIn("path=user-1-files%2Fdocs%2F", current_url)

    def test_user_can_find_object_via_search_form_in_ui(self):
        """Пользователь может найти файл или папку через форму поиска"""
