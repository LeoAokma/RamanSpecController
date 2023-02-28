class Settings:
    """
    设置类，主要是针对不同语言进行设置，目前尚未开始使用
    """
    def __init__(self, language):
        # Chinese = 0, English = 1
        if language == 'English':
            self.language = 1
        elif language == '简体中文':
            self.language = 0

        self.win_title = ['拉曼光谱控制程序 - v.1.1.0 作者: LeoAokma',
                          "Raman Spectroscopy Reader - v.1.1.0 by LeoAokma"][self.language]