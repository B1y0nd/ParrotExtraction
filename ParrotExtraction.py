#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   plftool.py
@Time    :   2024/02/22 10:44:56
@Author  :   b1y0nd 
@Version :   1.0
@Desc    :   extract kernel, bootparam, bootloader, installer and filesystem from parrot drones firmware.
'''

#############################################################
# 导入模块
import argparse
import os
import sys
import struct
import zlib
import lzma
#############################################################
# 全局变量
## 设置提取到的文件的命名
volume_config_file = "/volume_config.txt"
installer_file = "/installer.plf"
bootloader_file = "/bootloader.bin"
kernel_plf_file = "/main_boot.plf"
kernel_zImage_file = "/zImage"
kernel_gzip_file = "/kernel.gz"
kernel_lzma_file = "/kernel.xz"
bootparam_file = "/bootparams.txt"
filesystem_dir = "/filesystem"
## 固件头字段常量
P_HDR_MAGIC = "header_magic_number"
P_HDR_VER = "header_version"
P_HDR_SIZE = "header_size"
P_HDR_ENTRY_HDR_SIZE = "entry_header_size"
P_HDR_FILE_TYPE = "file_type"
P_HDR_ENTRYPOINT = "executable_entry_point"
P_HDR_TARGET_PLAT = "target_platform"
P_HDR_TARGET_APPL = "target_application"
P_HDR_HW_COMPAT = "hardware_compatibility"
P_HDR_MAJOR_VERSION = "major_version"
P_HDR_MINOR_VERSION = "minor_version"
P_HDR_BUGFIX_VERSION = "bugfix_version"
P_HDR_LANG_ZONE = "language_zone"
P_HDR_FILE_SIZE = "file_size"
## 条目头字段常量
P_ENTRY_TYPE = "entry_type"
P_ENTRY_SIZE = "entry_size"
P_ENTRY_CRC32 = "crc32"
P_ENTRY_LOADADDR = "load_address"
P_ENTRY_UNCOMPRESSED_SIZE = "uncompressed_size"
## 条目类型
ENTRY_VOLUME_CONFIG = 0x0B
ENTRY_INSTALLER = 0x0C
ENTRY_BOOTLOADER = 0x07
ENTRY_MAINBOOT = 0x03
ENTRY_FILESYSTEM = 0x09
## 分区数以及挂载的分区数据
NB_ENTRIES = "number_partitions"
P_VOLUME_DEVICE_NUM = "device_number"
P_VOLUME_TYPE = "volume_type"
P_VOLUME_NUM = "volume_number"
P_VOLUME_UNKNOWN = "unknown"
P_VOLUME_SIZE = "volume_size"
P_VOLUME_ACTION = "volume_action"
P_VOLUME_NAME = "volume_name"
P_VOLUME_MOUNT_NAME = "mount_name"
## 文件系统属性
FS_DIR = 0x04
FS_FILE = 0x08
FS_SYMLINK = 0x0A
P_TYPE = "type"
P_FILENAME = "file_name"
P_FILEPER = "file_permissions"
P_FILEDATA = "file_data"
P_DIRNAME = "directory_name"
P_DIRPER = "directory_permissions"
P_SYMLINK = "symbol_link"
## 文件信息统计
FILE_NUM = 0
DIR_NUM = 0
SYMLINK_NUM = 0
UNKNOWN_NUM = 0
#############################################################

class Logger(object):
    def __init__(self):
        self.output = sys.stdout
        self.log = False
        self.info = False
    def print_log(self, _message):
        if self.log:
            self.output.write("[>] " + _message + "\n")
    def print_info(self, _message):
        if self.info:
            self.output.write("[*] " + _message + "\n")
class FirmwareFile(object):
    def __init__(self, _file, _dir, _logger):
        self.firmware = _file
        self.outputdir = _dir
        self.logger = _logger
        self.properties = {}
        self.entries = []
        self.partitions = []
    def _u32_bytes_to_string(self, _bytes):
        return struct.unpack("4s", _bytes)[0]
    def _u32_bytes_to_int(self, _bytes):
        return struct.unpack("I", _bytes)[0]
    def _read_u32_bytes(self, _fhandle):
        return _fhandle.read(4)
    def _u16_bytes_to_short(self, _bytes):
        return struct.unpack("H", _bytes)[0]
    def _read_u16_bytes(self, _fhandle):
        return _fhandle.read(2)
    def _u8_bytes_to_chars(self, _fhandle, _len):
        name = b""
        for i in range(0, _len):
            name += self._read_u8_bytes(_fhandle)
        return name.decode("utf-8")
    def _read_u8_bytes(self, _fhandle):
        return _fhandle.read(1)
    def _read_string(self, _fhandle):
        name = b""
        byte = self._read_u8_bytes(_fhandle)
        while byte != b'\x00':
            name += byte
            byte = self._read_u8_bytes(_fhandle)
        return name.decode("utf-8")
    def parse_firmware(self):
        with open(self.firmware, "rb") as f:
            if self._read_firmware_header(f):
                self._extract_entries(f)
                self._recover_symlink()
                self._statistics_file_info()
            f.close()
    def _read_firmware_header(self, _fhandle):
        self.properties[P_HDR_MAGIC] = self._u32_bytes_to_string(self._read_u32_bytes(_fhandle))
        # 判断输入文件是否是parrot firmware
        start_next_loop = True
        if self.properties[P_HDR_MAGIC].decode("utf-8") != "PLF!":
            self.logger.print_log("File {} is not a parrot firmware!".format(self.firmware))
            start_next_loop = False
        else:
            pass
        self.properties[P_HDR_VER] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_SIZE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_ENTRY_HDR_SIZE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_FILE_TYPE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_ENTRYPOINT] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_TARGET_PLAT] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_TARGET_APPL] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_HW_COMPAT] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_MAJOR_VERSION] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_MINOR_VERSION] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_BUGFIX_VERSION] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_LANG_ZONE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[P_HDR_FILE_SIZE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        return start_next_loop
    def _extract_entries(self, _fhandle):
        while(_fhandle.tell() < self.properties[P_HDR_FILE_SIZE]):
            new_entry = self._extract_entry(_fhandle)
            self.entries.append(new_entry)
    def _extract_entry(self, _fhandle):
        f_entry = FirmwareEntry()
        f_entry.entry_properties[P_ENTRY_TYPE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        f_entry.entry_properties[P_ENTRY_SIZE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        f_entry.entry_properties[P_ENTRY_CRC32] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        f_entry.entry_properties[P_ENTRY_LOADADDR] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        f_entry.entry_properties[P_ENTRY_UNCOMPRESSED_SIZE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        if(f_entry.entry_properties[P_ENTRY_TYPE] == ENTRY_VOLUME_CONFIG):
            self._extract_volume_config(_fhandle, f_entry)
        elif (f_entry.entry_properties[P_ENTRY_TYPE] == ENTRY_INSTALLER):
            self._extract_installer(_fhandle, f_entry)
        elif (f_entry.entry_properties[P_ENTRY_TYPE] == ENTRY_BOOTLOADER):
            self._extract_bootloader(_fhandle, f_entry)
        elif (f_entry.entry_properties[P_ENTRY_TYPE] == ENTRY_MAINBOOT):
            self._extract_kernel(_fhandle, f_entry)
        elif (f_entry.entry_properties[P_ENTRY_TYPE] == ENTRY_FILESYSTEM):
            self._extract_filesystem(_fhandle, f_entry)
            reminder = f_entry.entry_properties[P_ENTRY_SIZE] % 4
            if reminder != 0:
                _fhandle.read(4 - reminder)
            else:
                pass
        return f_entry
    def _extract_volume_config(self, _fhandle, _fentry):
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        self.properties[NB_ENTRIES] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
        if not os.path.exists(self.outputdir):
            os.makedirs(self.outputdir)
            self.logger.print_log("Creates directory {}".format(self.outputdir))
        else:
            self.logger.print_log("Directory {} exists".format(self.outputdir))
        with open(self.outputdir + volume_config_file, 'w') as f:
            f.write("[volume_config]\n")
            self.logger.print_log("File {} creates".format(self.outputdir + volume_config_file))
            # self.logger.print_info("{} partition(s) found in {}".format(self.properties[NB_ENTRIES], self.firmware))
            for i in range(0, self.properties[NB_ENTRIES]):
                p_entry = Partition()
                p_entry.partition_properties[P_VOLUME_DEVICE_NUM] = self._u16_bytes_to_short(self._read_u16_bytes(_fhandle))
                p_entry.partition_properties[P_VOLUME_TYPE] = self._u16_bytes_to_short(self._read_u16_bytes(_fhandle))
                p_entry.partition_properties[P_VOLUME_NUM] = self._u16_bytes_to_short(self._read_u16_bytes(_fhandle))
                p_entry.partition_properties[P_VOLUME_UNKNOWN] = self._u16_bytes_to_short(self._read_u16_bytes(_fhandle))
                p_entry.partition_properties[P_VOLUME_SIZE] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
                p_entry.partition_properties[P_VOLUME_ACTION] = self._u32_bytes_to_int(self._read_u32_bytes(_fhandle))
                p_entry.partition_properties[P_VOLUME_NAME] = self._u8_bytes_to_chars(_fhandle, 32)
                p_entry.partition_properties[P_VOLUME_MOUNT_NAME] = self._u8_bytes_to_chars(_fhandle, 32)
                self.partitions.append(p_entry)
                p_entry_string = p_entry._object_to_string(p_entry)
                # self.logger.print_log(p_entry_string)
                # self.logger.print_info(p_entry_string)
                p_entry_string = p_entry_string + "\n"
                f.write(p_entry_string)
            f.close()
    def _extract_installer(self, _fhandle, _fentry):
        data = _fhandle.read(_fentry.entry_properties[P_ENTRY_SIZE])
        with open(self.outputdir + installer_file, 'wb') as f:
            f.write(data)
            f.close()
            self.logger.print_log("File {} creates".format(self.outputdir + installer_file))
            self.logger.print_info("Installer found. File {}".format(self.outputdir + installer_file))
    def _extract_bootloader(self, _fhandle, _fentry):
        data = _fhandle.read(_fentry.entry_properties[P_ENTRY_SIZE])
        with open(self.outputdir + bootloader_file, 'wb') as f:
            f.write(data)
            f.close()
            self.logger.print_log("File {} creates".format(self.outputdir + bootloader_file))
            self.logger.print_info("Bootloader found. File {}".format(self.outputdir + bootloader_file))
    def _extract_kernel(self, _fhandle, _fentry):
        data = _fhandle.read(_fentry.entry_properties[P_ENTRY_SIZE])
        with open(self.outputdir + kernel_plf_file, 'wb') as f:
            f.write(data)
            f.close()
            self.logger.print_log("File {} creates".format(self.outputdir + kernel_plf_file))
            self.logger.print_info("Kernel found. File {}".format(self.outputdir + kernel_plf_file))
        with open(self.outputdir + kernel_plf_file, 'rb') as f:
            # 找到zImage
            entry_03_firmware_header = f.read(56)
            entry_03_00_header_1 = f.read(4)
            entry_03_00_size = struct.unpack("I", f.read(4))[0]
            entry_03_00_header_2 = f.read(12)
            entry_03_00_data = f.read(entry_03_00_size)
            with open(self.outputdir + kernel_zImage_file, 'wb') as f_zimage:
                f_zimage.write(entry_03_00_data)
                f_zimage.close()
                self.logger.print_log("File {} creates".format(self.outputdir + kernel_zImage_file))
                self.logger.print_info("Kernel zImage file creates. File {}".format(self.outputdir + kernel_zImage_file))
            # 找到gzip或者lzma压缩的内核
            gzip_start_index = entry_03_00_data.find(b'\x1f\x8b\x08')
            lzma_start_index = entry_03_00_data.find(b'\x5d\x00\x00')
            flag = False
            if gzip_start_index != -1 and flag is False:
                gzip_end_index = self._find_gzip_end_pos(entry_03_00_data, gzip_start_index)
                if gzip_end_index != -1:
                    flag = True
                    gzip_data = entry_03_00_data[gzip_start_index:gzip_end_index]
                    with open(self.outputdir + kernel_gzip_file, 'wb') as f_gzip:
                        f_gzip.write(gzip_data)
                        f_gzip.close()
                        self.logger.print_log("File {} creates".format(self.outputdir + kernel_gzip_file))
                        self.logger.print_info("Kernel gzip file creates. File {}".format(self.outputdir + kernel_gzip_file))
            if lzma_start_index != -1 and flag is False:
                lzma_end_index = self._find_lzma_end_pos(entry_03_00_data, lzma_start_index)
                if lzma_end_index != -1:
                    lzma_data = entry_03_00_data[lzma_start_index:lzma_end_index]
                    with open(self.outputdir + kernel_lzma_file, 'wb') as f_lzma:
                        f_lzma.write(lzma_data)
                        f_lzma.close()
                        self.logger.print_log("File {} creates".format(self.outputdir + kernel_lzma_file))
                        self.logger.print_info("Kernel lzma file creates. File {}".format(self.outputdir + kernel_lzma_file))
            # 找到bootparam
            entry_03_07_header_1 = f.read(4)
            entry_03_07_size = struct.unpack("I", f.read(4))[0]
            entry_03_07_header_2 = f.read(12)
            entry_03_07_data = f.read(entry_03_07_size)
            with open(self.outputdir + bootparam_file, 'wb') as f_bootparam:
                f_bootparam.write(entry_03_07_data)
                f_bootparam.close()
                self.logger.print_log("File {} creates".format(self.outputdir + bootparam_file))
                self.logger.print_info("Bootparam file creates. File {}".format(self.outputdir + bootparam_file))
            f.close()
    def _find_gzip_end_pos(self, _data, _startindex):
        end_index = len(_data) - 4
        while end_index >= 0:
            computed_size = struct.unpack('I', _data[end_index : end_index + 4])[0]
            try:
                uncompressed_data = zlib.decompress(_data[_startindex : end_index + 4], zlib.MAX_WBITS | 16)
                uncompressed_size = len(uncompressed_data)
                if uncompressed_size == computed_size:
                    return end_index + 4
            except Exception as e:
                pass
            end_index = end_index - 1
        return -1
    def _find_lzma_end_pos(self, _data, _startindex):
        end_index = len(_data) - 4
        while end_index >= 0:
            computed_size = struct.unpack('I', _data[end_index : end_index + 4])[0]
            try:
                uncompressed_data = lzma.decompress(_data[_startindex : end_index])
                uncompressed_size = len(uncompressed_data)
                if uncompressed_size == computed_size:
                    return end_index + 4
            except Exception as e:
                pass
            end_index = end_index - 1
        return -1
    def _extract_filesystem(self, _fhandle, _fentry):
        if not os.path.exists(self.outputdir + filesystem_dir):
            os.makedirs(self.outputdir + filesystem_dir)
            self.logger.print_log("Creates filesystem directory {}".format(self.outputdir + filesystem_dir))
        global FILE_NUM, DIR_NUM, SYMLINK_NUM, UNKNOWN_NUM
        is_compressed = False
        if _fentry.entry_properties[P_ENTRY_UNCOMPRESSED_SIZE] > 0:
            is_compressed = True
        if not is_compressed:
            # 文件名或者目录名
            name = self._read_string(_fhandle)
            # 文件类型和权限
            flags = self._read_u32_bytes(_fhandle)
            permissions, file_type = self._get_file_type(flags)
            _fentry.entry_properties[P_TYPE] = file_type
            self._read_u32_bytes(_fhandle)
            self._read_u32_bytes(_fhandle)
            # 文件内容
            if file_type == FS_DIR:
                _fentry.entry_properties[P_DIRNAME] = name
                _fentry.entry_properties[P_DIRPER] = oct(permissions)
                DIR_NUM = DIR_NUM + 1
                dir_full_name = self.outputdir + filesystem_dir + '/' + name
                if not os.path.exists(dir_full_name):
                    os.makedirs(dir_full_name, mode=permissions)
                    self.logger.print_log("Directory {} creates. Permissions is {}".format(dir_full_name, oct(permissions)))
                else:
                    os.chmod(dir_full_name, permissions)
                    self.logger.print_log("Directory {} exists. Permissions is {}".format(dir_full_name, oct(permissions)))
            elif file_type == FS_FILE:
                _fentry.entry_properties[P_FILENAME] = name
                _fentry.entry_properties[P_FILEPER] = oct(permissions)
                FILE_NUM = FILE_NUM + 1
                file_data = _fhandle.read(_fentry.entry_properties[P_ENTRY_SIZE] - len(name) - 1 - 12)
                _fentry.entry_properties[P_FILEDATA] = file_data
                file_full_name = self.outputdir + filesystem_dir + '/' + name
                dir_name = os.path.dirname(file_full_name)
                file_name = os.path.basename(file_full_name)
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                with open(file_full_name, 'wb') as f:
                    f.write(file_data)
                    f.close()
                    self.logger.print_log("File {} creates. Permissions is {}".format(file_full_name, oct(permissions)))
                os.chmod(file_full_name, permissions)
            elif file_type == FS_SYMLINK:
                # 在文件创建工作完成之后，再进行恢复符号链接工作，这里先不进行。
                _fentry.entry_properties[P_FILENAME] = name
                SYMLINK_NUM = SYMLINK_NUM + 1
                symbol_link_data = self._read_string(_fhandle)
                _fentry.entry_properties[P_SYMLINK] = symbol_link_data
                self.logger.print_log("This is a symbol link. {} --> {}".format(name, symbol_link_data))
            elif file_type == 0x02:
                UNKNOWN_NUM = UNKNOWN_NUM + 1
                # 特殊文件dev/console: b'\xb6\x21' AR_Drone_v1.5.1.plf
                data = _fhandle.read(_fentry.entry_properties[P_ENTRY_SIZE] - len(name) - 1 - 12)
                self.logger.print_log("Unknown type file! File name is {}. File data is {}".format(name, data))
        else:
            FILE_NUM = FILE_NUM + 1
            compressed_data = _fhandle.read(_fentry.entry_properties[P_ENTRY_SIZE])
            name, flags, data = self._uncompress_file(_fentry, compressed_data)
            permissions, file_type = self._get_file_type(flags)
            _fentry.entry_properties[P_TYPE] = file_type
            _fentry.entry_properties[P_FILENAME] = name
            _fentry.entry_properties[P_FILEPER] = oct(permissions)
            _fentry.entry_properties[P_FILEDATA] = data
            file_full_name = self.outputdir + filesystem_dir + '/' + name
            dir_name = os.path.dirname(file_full_name)
            file_name = os.path.basename(file_full_name)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            with open(file_full_name, 'wb') as f:
                f.write(data)
                f.close()
                self.logger.print_log("Uncompressed File {} creates. Permissions is {}".format(file_full_name, oct(permissions)))
            os.chmod(file_full_name, permissions)
    def _get_file_type(self, _flags):
        permissions = int(oct(int.from_bytes(_flags, byteorder='little') & 0x0FFF), 8)
        filetype = (int.from_bytes(_flags, byteorder='little') & 0xF000) >> 12
        return permissions, filetype
    def _recover_symlink(self):
        for entry in self.entries:
            if entry.entry_properties.get(P_TYPE) == FS_SYMLINK:
                file_full_name = self.outputdir + filesystem_dir + '/' + entry.entry_properties[P_FILENAME]
                symbol_full_name = entry.entry_properties[P_SYMLINK]
                os.symlink(symbol_full_name, file_full_name)
                self.logger.print_log("Symbol link creats. {} --> {}".format(file_full_name, symbol_full_name))
    def _uncompress_file(self, _fentry, _fdata):
        uncompressed_data = zlib.decompress(_fdata, zlib.MAX_WBITS | 16)
        if len(uncompressed_data) == _fentry.entry_properties[P_ENTRY_UNCOMPRESSED_SIZE]:
            self.logger.print_log("Uncompress file is successful!")
        else:
            self.logger.print_log("Uncompress file fails!")
        data = uncompressed_data.split(b'\x00', 1)
        filename = data[0].decode('utf-8')
        filedata = data[1]
        flags = filedata[0:4]
        return filename, flags, filedata[12:]
    def _statistics_file_info(self):
        self.logger.print_info("Filesystem: Creates {} file(s), {} directory(s) and {} symbol link(s). Meanwhile, {} file(s) belongs to unknown type.".format(FILE_NUM, DIR_NUM, SYMLINK_NUM, UNKNOWN_NUM))
class FirmwareEntry(object):
    def __init__(self):
        self.entry_properties = {}
class Partition(object):
    def __init__(self):
        self.partition_properties = {}
    def _object_to_string(self, p_entry):
        return "Mount: {}, Device: 0x{:04x}, Volume:[Name: {}, Type: {:04x}, ID: {:04x}, Size: {}, Action: {:08x}".format(
            p_entry.partition_properties[P_VOLUME_MOUNT_NAME],
            p_entry.partition_properties[P_VOLUME_DEVICE_NUM],
            p_entry.partition_properties[P_VOLUME_NAME],
            p_entry.partition_properties[P_VOLUME_TYPE],
            p_entry.partition_properties[P_VOLUME_NUM],
            p_entry.partition_properties[P_VOLUME_SIZE],
            p_entry.partition_properties[P_VOLUME_ACTION]
        )
def do_extract(input_file, output_dir, is_log, is_info):
    logger = Logger()
    logger.log = is_log
    logger.info = is_info
    logger.print_log("Processing file: {}".format(input_file))
    # 创建固件文件对象，并解析固件头和条目。
    firmware = FirmwareFile(input_file, output_dir, logger)
    firmware.parse_firmware()

def main():
    # 命令行解析器
    parser = argparse.ArgumentParser(description="A program to extract kernel, bootparam, bootloader, installer and filesystem from parrot drones firmware.")
    parser.add_argument('-r', '--read', required=True, help='Parrot firmware file or Parrot firmware file directory to read.')
    parser.add_argument('-w', '--write', default=os.getcwd(), help='Output directory into which files will be extracted to.')
    parser.add_argument('-l', '--log', action='store_true', help='True: extract files and display log about decompression process.')
    parser.add_argument('-i', '--info', action='store_true', help='True: extract files and display infomation about the overall extraction results.')
    args = parser.parse_args()
    # 读取命令行参数
    output_dir = args.write
    is_log = args.log
    is_info = args.info
    # 判断是对单个文件进行提取还是对目录下所有文件进行提取，并执行提取操作。
    if os.path.isfile(args.read):
        input_file = args.read
        full_filename = os.path.basename(input_file)
        filename, _ = os.path.splitext(full_filename)
        do_extract(input_file, output_dir + '/' + filename, is_log, is_info)
    elif os.path.isdir(args.read):
        input_dir = args.read
        input_dir_files = [os.path.join(input_dir, file) for file in os.listdir(input_dir)]
        for input_file in input_dir_files:
            full_filename = os.path.basename(input_file)
            filename, _ = os.path.splitext(full_filename)
            do_extract(input_file, output_dir + '/' + filename, is_log, is_info)

if __name__ == "__main__":
    main()
