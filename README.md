# ParrotExtraction  
A tool to extract kernel, bootparam, bootloader, installer and filesystem from parrot drones firmware files.  
# Usage  
python3 ./FirmwareExtract.py -r <firmware> -w <output_dir> [-l] [-i]  

A program to extract kernel, bootparam, bootloader, installer and filesystem from parrot drones firmware.  

optional arguments:  
  -h, --help            show this help message and exit  
  -r READ, --read READ  Parrot firmware file or Parrot firmware file directory  
                        to read.  
  -w WRITE, --write WRITE  
                        Output directory into which all files will be extracted  
                        to.  
  -l, --log             True: extract files and display log about  
                        decompression process.  
  -i, --info            True: extract files and display infomation about the overall  
                        extraction results.  
# Example  
python3 ./FirmwareExtract.py -r ./drone/disco_update_0.plf -w ./out -i  
Once executed, ParrotExtraction.py will analyze the given firmware and extract information.  
All results will be found in the out directory.  
All results include bootloader(bootloader.bin), bootparam(bootparams.txt), installer(installer.plf), kernel(main_boot.plf->zImage->kernel.gz), filesystem(filesystem).  
# Test  
Testing on firmwares for all different models of drones from the paroot manufacturer, with a success rate of 100% extraction.  
The testing dataset is names dataset.  
