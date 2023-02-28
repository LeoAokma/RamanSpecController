import os

file_dir = input('请输入待统计的日志文件夹\n')
software = input("请输入挖矿使用的软件\n(A=NB Miner, B=GMiner, C=Team Red Miner)\n")
logs = os.listdir(file_dir)
print(logs)
print("文件数{}".format(len(logs)))
count_all = 0
for log in logs:
    with open("{}/{}".format(file_dir, log), 'r') as file:
        count = 0
        lines = file.readlines()
        for _ in lines:
            if software == 'A':
                if 'Share accepted,' in _:
                    count += 1
            elif software == 'B':
                if ' accepted ' in _:
                    count += 1
            elif software == 'C':
                if ' share accepted. ' in _:
                    count += 1
    count_all += count

print("份额数：{}".format(count_all))
os.system('pause')
