import os
from pathlib import Path


class Anbernic:
    
    def __init__(self):
        self.__sd1_rom_storage_path = "/mnt/mmc/Roms"
        self.__sd2_rom_storage_path = "/mnt/sdcard/Roms"

        self.__rom_folder_mapping = {
            "PSP": "PSP",
            "PS": "PS",
            "GBA": "GBA",
            "GBC": "GBC",
            "GB": "GB",
            "NDS": "NDS",
            "N64": "N64",
        }
        self.__current_sd = 2

    def _is_sd2_available(self):
        sd2_path = "/mnt/sdcard"
        return os.path.ismount(sd2_path)

    def get_sd1_storage_path(self):
        return self.__sd1_rom_storage_path

    def get_sd2_storage_path(self):
        return self.__sd2_rom_storage_path
    
    def get_sd1_storage_console_path(self, console):
        return os.path.join(self.__sd1_rom_storage_path, self.__rom_folder_mapping[console])

    def get_sd2_storage_console_path(self, console):
        return os.path.join(self.__sd2_rom_storage_path, self.__rom_folder_mapping[console])
    
    def set_sd_storage(self, sd):
        if sd == 1 or sd == 2:
            if sd == 2 and not self._is_sd2_available():
                sd = 1
            self.__current_sd = sd
    
    def get_sd_storage(self):
        if self.__current_sd == 1:
            return 1
        if self._is_sd2_available():
            return 2
        else:
            self.__current_sd = 1
            return 1

    def switch_sd_storage(self):
        if self.__current_sd == 1:
            if self._is_sd2_available():
                self.__current_sd = 2
        else:
            self.__current_sd = 1
    
    def get_sd_storage_path(self):
        if self.__current_sd == 1:
            return self.get_sd1_storage_path()
        else:
            if not self._is_sd2_available():
                self.__current_sd = 1
                return self.get_sd1_storage_path()
            return self.get_sd2_storage_path()
    
    def get_sd_storage_console_path(self, console):
        if self.__current_sd == 1:
            return self.get_sd1_storage_console_path(console)
        else:
            if not self._is_sd2_available():
                self.__current_sd = 1
                return self.get_sd1_storage_console_path(console)
            return self.get_sd2_storage_console_path(console)