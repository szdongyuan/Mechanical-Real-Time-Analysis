from pathlib import Path
import webbrowser


def open_html_in_default_browser(html_file_path: str) -> bool:
    """
    使用系统默认浏览器打开指定的 HTML 文件。

    :param html_file_path: HTML 文件的路径
    :return: 打开成功返回 True，失败返回 False
    """
    if not html_file_path:
        return 0

    try:
        path = Path(html_file_path).expanduser().resolve()

        if not path.exists() or not path.is_file():
            return False

        # 生成 "file://..." 的本地文件 URL，并用默认浏览器打开
        file_url = path.as_uri()
        return webbrowser.open(file_url)
    except Exception:
        # 任意异常都视为打开失败
        return 2


if __name__ == "__main__":
    # 简单测试用例：手动修改为你要查看的 HTML 文件路径
    test_html = "D:/gqgit/new_project/reports/Report_250911_074547.wav.html"
    open_html_in_default_browser(test_html)


