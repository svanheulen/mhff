import argparse
import array
import os


def extract_package(package_file, out_path):
    with open(package_file, 'rb') as package:
        file_count = array.array('I', package.read(4))[0]
        file_info = array.array('I', package.read(file_count * 8))
        for i in range(file_count):
            package.seek(file_info[i*2])
            open(os.path.join(out_path, '%s-%04d' % (package_file, i)), 'wb').write(package.read(file_info[i*2+1]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts all files from a package file from Monster Hunter')
    parser.add_argument('packagefile', help='package file to extract')
    parser.add_argument('outpath', nargs='?', default='', help='path to extract to')
    args = parser.parse_args()
    extract_package(args.packagefile, args.outpath)

