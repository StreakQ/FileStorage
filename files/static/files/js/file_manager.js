function getFileCountText(count) {
    // Простой пример склонения для русского языка
    if (count === 1) return 'файл';
    if (count >= 2 && count <= 4) return 'файла';
    return 'файлов';
}
// --- Конец вспомогательной функции ---

document.addEventListener('DOMContentLoaded', function () {
    // --- 1. Проверяем Bootstrap ---
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap не загружен');
        return;
    }

    // --- 2. Принудительная инициализация всех dropdown (опционально, если возникают проблемы) ---
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
        const instance = bootstrap.Dropdown.getInstance(toggle);
        if (instance) instance.dispose();
        new bootstrap.Dropdown(toggle);
    });

    // --- 3. Модальное окно переименования ---
    document.querySelectorAll('[data-bs-toggle="modal"][data-s3-key]').forEach(button => {
        button.addEventListener('click', function () {
            const s3Key = this.getAttribute('data-s3-key');
            const itemName = this.getAttribute('data-item-name');

            // Убедитесь, что ID элементов в HTML совпадают с этими
            const s3KeyInput = document.getElementById('s3KeyInput'); // <-- Проверьте ID
            const newNameInput = document.getElementById('newName');  // <-- Проверьте ID

            if (s3KeyInput) s3KeyInput.value = s3Key;
            if (newNameInput) newNameInput.value = itemName;

        });
    });

    // --- 4. Кнопка "Сохранить" в модальном окне ---
    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            const renameForm = document.getElementById('renameForm'); // <-- Проверьте ID
            if (renameForm) {
                 renameForm.submit();
                 console.log("Форма отправлена")
            } else {
                 console.error("Форма переименования '#renameForm' не найдена.");
            }
        });
    }

    // --- 5. Форма создания папки ---
    const creationBtn = document.getElementById('showCreateForm'); // <-- Проверьте ID
    const createForm = document.getElementById('createFolderForm'); // <-- Проверьте ID
    const cancelCreate = document.getElementById('cancelCreate');   // <-- Проверьте ID

    if (creationBtn && createForm && cancelCreate) {
        creationBtn.addEventListener('click', function () {
            createForm.style.display = 'block';
            this.style.display = 'none';
            const folderNameInput = createForm.querySelector('input[name="folder_name"]');
            if (folderNameInput) folderNameInput.focus();
        });

        cancelCreate.addEventListener('click', function () {
            createForm.style.display = 'none';
            creationBtn.style.display = 'inline-block';
        });
    }

    // --- 6. Форма загрузки файлов ---
    const fileInput = document.getElementById('fileInput'); // <-- Проверьте ID
    const customUploadBtn = document.getElementById('customUploadBtn'); // <-- Проверьте ID
    const uploadBtn = document.getElementById('uploadBtn'); // <-- Проверьте ID

    if (fileInput && customUploadBtn && uploadBtn) {
        // --- 6.1. Обработчик клика по кнопке "Выбрать файлы" ---
        customUploadBtn.addEventListener('click', function () {
            fileInput.click(); // Программно нажимаем на скрытое поле <input type="file">
        });

        // --- 6.2. Обработчик изменения (выбора) файлов в input'e ---
        fileInput.addEventListener('change', function () {
            const selectedFiles = fileInput.files; // FileList объект с выбранными файлами
            const fileCount = selectedFiles.length;

            if (fileCount > 0) {
                // Если файлы выбраны
                uploadBtn.disabled = false; // Активируем кнопку "Загрузить"
                // Обновляем текст кнопки, показывая количество выбранных файлов
                uploadBtn.textContent = `Загрузить (${fileCount} ${getFileCountText(fileCount)})`;
            } else {
                // Если файлы сняты (например, пользователь отменил выбор)
                uploadBtn.disabled = true; // Деактивируем кнопку "Загрузить"
                uploadBtn.textContent = 'Загрузить (0 файлов)'; // Возвращаем исходный текст
            }
        });

        // --- 6.3. Обработчик отправки формы загрузки ---
        const uploadForm = fileInput.closest('form'); // Находим форму, к которой принадлежит input
        if (uploadForm) {
             uploadForm.addEventListener('submit', function(event) {
                 if (fileInput.files.length === 0) {
                     event.preventDefault(); // Остановить отправку, если файлы не выбраны
                     alert('Пожалуйста, выберите файлы для загрузки.');
                 }
                 // Здесь можно добавить логику для отображения прогресса загрузки
                 console.log("Форма загрузки отправляется...");
             });
        } else {
             console.warn("Форма загрузки не найдена для input'a с id 'fileInput'.");
        }
    } else {
         console.warn("Элементы для формы загрузки (fileInput, customUploadBtn, uploadBtn) не найдены.");
    }

});