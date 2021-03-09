import cv2


def calc_im_hash(filename: str, bit: int = 8):
    image = cv2.imread(filename)  # Прочитаем картинку
    resized = cv2.resize(image, (bit, bit), interpolation=cv2.INTER_AREA)  # Уменьшим картинку
    gray_image = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)  # Переведем в черно-белый формат
    avg = gray_image.mean()  # Среднее значение пикселя
    ret, threshold_image = cv2.threshold(gray_image, avg, 255, 0)  # Бинаризация по порогу

    # Рассчитаем хэш
    _hash = ""
    for x in range(bit):
        for y in range(bit):
            val = threshold_image[x, y]
            if val == 255:
                _hash = _hash + "1"
            else:
                _hash = _hash + "0"

    return _hash


def compare_hash(hash1: str, hash2: str) -> int:
    """Сравнивает бинарные хеши картинок"""

    n = f'{int(hash1, 2) ^ int(hash2, 2):b}'
    return n.count('1')
