# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 16:20:03 2019

@author: liang.xue
"""
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#np.random.seed(datetime.datetime.now())

class UtilsMath(object):
    def __init__(self, randomSeed = 1):
        """Default seed for random data is 1, user can input seed to change it everytime
        """
        np.random.seed(randomSeed)
    
    def drawUniformDiscreteDataset(self, lowRange, highRange, dataNumbers):
        """Draw a discrete random set of integer data following uniform distribution
            - lowRange: low range of number to be generated
            - highRange: high range of the number for set the limit to be generated
            - dataNumbers: data set size to be generated
            
            **Explain: as the function's high range is exclusive, when we input the data, the high range need to be added by 1 -- [lowRange,highRange+1)
        """

        return np.random.randint(lowRange, highRange + 1, dataNumbers)

    def demo(self):
        low = 1
        high = 3
        numbers = 1000
        dataSet = self.drawUniformDiscreteDataset(low, high, numbers)
        count,bins,ignored = plt.hist(dataSet, 20, facecolor='green')
        print(count)
        print(ignored)
        plt.plot(bins, np.ones_like(bins), linewidth=2, color='r')
        plt.show()

    def outputResult(self, dataDict, columnNames, outputPath, fileName):
        #data_tuples = list(zip(inputListSet))
        outputDf = pd.DataFrame([a for a in dataDict.items()], columns = columnNames)
        #outputDf = pd.DataFrame(data_tuples, columns = columnNames)

        writer = pd.ExcelWriter(outputPath+fileName, engine='xlsxwriter')
        outputDf.to_excel(writer, fileName.split('.')[0], index=False)

        writer.save()

if __name__ == "__main__":
    utils = UtilsMath()
    sectorNumbers = 42
    nsblTypeNumbers = 4
    totalNSBLProjects = 183
    outputPath = r"C:\\temp\\"
    
    outputNameSector = 'sectordraw_{0}.xlsx'.format(datetime.date.today())
    outputNameNsblType = 'nsbltypedraw_{0}.xlsx'.format(datetime.date.today())
    sectorDrawResultColumn = ['Index', 'SectorNumber']
    nsblTypeDrawResultColumn = ['Index', 'NsblType']

    
    rangeList = [*range(1, totalNSBLProjects+1, 1)]  #unpacking range by using a *
    
    dataResultSector = utils.drawUniformDiscreteDataset(1, sectorNumbers, totalNSBLProjects)
    #sectorTupleList = list(zip(rangeList, dataResultSector.tolist()))
    sectorDict = dict(zip(rangeList, dataResultSector.tolist()))

    dataResultNsblType = utils.drawUniformDiscreteDataset(1, nsblTypeNumbers, totalNSBLProjects)
    nsblTypeDict = dict(zip(rangeList, dataResultNsblType.tolist()))

    utils.outputResult(sectorDict, sectorDrawResultColumn, outputPath, outputNameSector)
    utils.outputResult(nsblTypeDict, nsblTypeDrawResultColumn, outputPath, outputNameNsblType)
    
    
    