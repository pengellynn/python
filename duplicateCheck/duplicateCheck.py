import os
import re
import xlrd
import xlwt


def getStudentDict(nameListPath):
    workbook = xlrd.open_workbook(nameListPath)
    sheet = workbook.sheet_by_index(0)
    stuDict = dict()
    for row in range(1, sheet.nrows):
        stuDict.__setitem__(sheet.cell_value(row, 0), sheet.cell_value(row, 1))
    return stuDict


codeFilePathList = []


def getCodeFilePaths(path):
    fileList = os.listdir(path)  # 获取path目录下所有文件
    for filename in fileList:
        pathTemp = os.path.join(path, filename)  # 获取path与filename组合后的路径
        if os.path.isdir(pathTemp):  # 如果是目录
            getCodeFilePaths(pathTemp)  # 则递归查找
        elif pathTemp.endswith('.h') or pathTemp.endswith('.cpp'):  # 不是目录,则比较后缀名
            codeFilePathList.append(pathTemp)


def mergeCodeFiles(student, codePaths, resultPath):
    resultFileName = os.path.join(resultPath, student[0] + '.cpp')
    with open(resultFileName, 'ab') as resultFile:
        for path in codePaths:
            with open(path, 'rb') as f:
                content = f.read()
                resultFile.write(content)


def duplicateChecking(appPath, commands):
    os.chdir(appPath)
    for command in commands:
        os.system(command)


def extractNames(stuDict, resultNameListPath, originalReportPath):
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('查重结果名单')
    headerStyle = xlwt.easyxf('font: bold on')
    keyStyle = xlwt.easyxf('font: color-index red')
    normalStyle = xlwt.easyxf('font: color-index black')
    sheet.write(0, 0, '人名1', headerStyle)
    sheet.write(0, 1, '人名2', headerStyle)
    sheet.write(0, 2, '重复率', headerStyle)
    stuPattern = re.compile('[0-9]{11}')
    probPattern = re.compile('[0-9]{1,3}\s%')
    with open(originalReportPath, 'r') as rf:
            lines = rf.readlines()
            i = 1
            for line in lines:
                if line.find('consists for') != -1:
                    stuIds = stuPattern.findall(line)
                    stuName1 = stuDict.get(stuIds[0])
                    stuName2 = stuDict.get(stuIds[1])
                    prob = probPattern.search(line).group(0).replace(' ', '')
                    style = keyStyle if int(
                        prob.rstrip('%')) > 80 else normalStyle
                    sheet.write(i, 0, stuName1, style)
                    sheet.write(i, 1, stuName2, style)
                    sheet.write(i, 2, prob, style)
                    i = i + 1
            workbook.save(resultNameListPath)


def starter(appPath, nameListPath, targetPath):
    stuDict = getStudentDict(nameListPath)
    unCommittedStudents = dict()
    for stu in stuDict.items():
        fileList = os.listdir(targetPath)
        for filename in fileList:
            stuPath = os.path.join(targetPath, filename)
            if filename.find(stu[1]) != -1 and os.path.isdir(stuPath):
                getCodeFilePaths(stuPath)
        if len(codeFilePathList) != 0:
            mergeCodeFiles(stu, codeFilePathList, appPath)
        else:
            unCommittedStudents.__setitem__(stu[0], stu[1])
        codeFilePathList.clear()

    if (len(unCommittedStudents) != 0):
        path = os.path.join(appPath, "未提交代码学生名单.xls")
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('未提交代码学生名单')
        headerStyle = xlwt.easyxf('font: bold on')
        sheet.write(0, 0, '学号', headerStyle)
        sheet.write(0, 1, '名字', headerStyle)
        i = 1
        for id, name in unCommittedStudents.items():
            sheet.write(i, 0, id)
            sheet.write(i, 1, name)
            i = i + 1
        workbook.save(path)

    commands = []
    command1 = "sim_c++ -o shixi.txt -p *.cpp"
    command2 = "sim_c++ -o shixi60.txt -t 60 -p *.cpp"
    commands.append(command1)
    commands.append(command2)
    duplicateChecking(appPath, commands)

    resultNameListPath = os.path.join(appPath, '查重结果名单(大于60%).xls')
    originalReportPath = os.path.join(appPath, 'shixi60.txt')
    extractNames(stuDict, resultNameListPath, originalReportPath)


if __name__ == "__main__":
    appPath = r'C:\Users\29040\Desktop\数据结构课\sim_exe_3_0_2'
    nameListPath = r"C:\Users\29040\Desktop\数据结构课\学生名单.xlsx"
    targetPath = r"C:\Users\29040\Desktop\课程设计\汇总\题1"
    starter(appPath, nameListPath, targetPath)
    print('查重成功！')
