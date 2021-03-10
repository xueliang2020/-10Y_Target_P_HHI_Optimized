# -*- coding: utf-8 -*-
"""
Created on Thu May 28 13:00:57 2018
@author: liang.xue

Description:
	adjusted version of GDP Proxy script
"""
import sys
import datetime
import pandas as pd

sys.path.append("..") #to be used for importing upper level folder result

from utils_target_p import UtilsTgtPortfolioBuilder
from config import ADJUSTMENT_FACTOR_RISK_LIMIT, PROJECTION_YEAR, RISK_LIMIT_DICT_SPB_ASSUMPTIONS

class NonSBLPortfolioBuilder(object):
    def __init__(self, sblCountryWeightsDict):
        self.countriesToAdjust = []
        self.countriesNotToAdjust = []
        self.nonRegionalCountriesNotToAdjust = []
        
        self.sblCountryWeightsDict = sblCountryWeightsDict
        self.utils = UtilsTgtPortfolioBuilder()
        
        self.nonRegional_NSBLMembers = self.utils.getMemberList(isGetRegional = False, isGetSBL = False)
        #get country full list based on initial NSBL country weights in decending order
        self.fullCountryList = self.utils.getCountryList(isGetSBL = False)

        #self.originalCountryWeights_SBL = self.utils.getOriginalCountryWeights(isGetSBL = True)
        #get original max
        self.maxWeight_SBL = max(sblCountryWeightsDict.values())
        #= self.utils.getMaxMinWeights(self.utils.originalCountryWeights_SBL)

        self.originalCountryWeights_NSBL = self.utils.originalCountryWeights_NSBL
        
        #adjust China weights to make it not bigger than 10%
        #self.originalCountryWeights_NSBL = self.adjustNSBLIndividualCountryExposure(self.originalCountryWeights_NSBL, isAdjustChinaExposure = True)
        
        #adjust country weights to see if any country have weights that bigger than the max(SBL), if so adjust it to other countries proportionally
        #isOverMaxSbl = self._validateOverMaxSblLimit(self.originalCountryWeights_NSBL, sblCountryWeightsDict)
        #if isOverMaxSbl:
        #    self.originalCountryWeightsList_NSBL, self.originalCountryWeights_NSBL = self.adjustNSBLIndividualCountryExposure(self.originalCountryWeights_NSBL, isAdjustMaxWeight = True)

        self.nsblTargetRating = self.utils.getTargetRating(isGetSBL = False)
        self.nsblTargetPD = self.utils.getTargetPD(isGetSBL = False)

        #self.countryPDList = self.utils.getCountryPDList(isGetSBL = False, countryWeightsDictInput = self.originalCountryWeights_NSBL)
        self.highRatingCountryWeightDict = self.utils.getHighRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = self.originalCountryWeights_NSBL)
        self.lowRatingCountryWeightDict = self.utils.getLowRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = self.originalCountryWeights_NSBL)

        self.lowRatingCountryRatingDict = self.utils.getLowRatingCountryDict(isGetSBL = False)
        self.lowRatingCountryRatingDict = self.utils.reOrderCountryWeightDict(self.lowRatingCountryRatingDict, reverse = True) #reorder to decending by rating

        self.getMinRatingWeightDict = self.utils.getMinRatingWeightDict(isGetSBL = False)
        #self.lowRatingDf = self.utils.getSortedLowerRatingDf(isGetSBL = False, countryWeightsDictInput = self.originalCountryWeights_NSBL)

    def updateCountryWeights(self, updatedCountryWeightsDict):
        """Update Country Weights and Ordering After each Adjustment Cycle
        """
        self.fullCountryList = self.utils.getCountryList(countryWeightsDictInput = updatedCountryWeightsDict)
        self.countriesToAdjust = list(set(self.countriesToAdjust)) #remove duplicates
        self.nonRegionalCountriesNotToAdjust = list(set(self.nonRegionalCountriesNotToAdjust)) #remove duplicates
        return self.utils.reOrderCountryWeightDict(updatedCountryWeightsDict, reverse = True)

    def _validateOverMaxSblLimit(self, countryWeightsNSBL, countryWeightsSBL):
        maxSBLWeight = max(countryWeightsSBL.values())
        nsblWeights = list(countryWeightsNSBL.values())
        validateResult = [True for nweight in nsblWeights if nweight > maxSBLWeight]
        return any(validateResult)

    def _valiadateChinaLimit(self, countryWeightsDict):
        chinaWeights = countryWeightsDict.get('CHN')
        return chinaWeights > RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('China').get('NSBL')

    def _validateWeightedAverageRatingLimit(self, countryWeightsDict):
        """Weighted average rating should meet bank's AAA target rating: 
            - Sovereign: 6
            - Non-Sovereign: 7
        """
        countryWeights = list(countryWeightsDict.values())
        countryPDDict = self.utils.getCountryPDDict(isGetSBL = False)
        weightAveragePD = sum([weight * countryPDDict.get(country,0) for country, weight in countryWeightsDict.items()]) / sum(countryWeights)
        print("weighted average rating:{0}".format(weightAveragePD))

        #TODO: for debugging purpose, to be deleted
        if weightAveragePD < 0.018:
            print("Bingo!")
        return bool(weightAveragePD >= self.nsblTargetPD)

    def _valiadateNonRegionalLimit(self, countryWeightsDict):
        nonRegionalWeightsTotal = sum([countryWeightsDict.get(country, 0) for country in self.nonRegional_NSBLMembers])
        if round(nonRegionalWeightsTotal, 4) > RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('Non_Regional').get('NSBL'):
            return {country:weight for country, weight in countryWeightsDict.items() if country in self.nonRegional_NSBLMembers}
        else:
            return {}

    def _validateMaxSBLConstrain(self, coutryWeights):
        return {country:weight for country, weight in coutryWeights.items() if ( (weight >= self.maxWeight_SBL) or ((weight + ADJUSTMENT_FACTOR_RISK_LIMIT) >= self.maxWeight_SBL))}

    def adjustNSBLIndividualCountryExposure(self, countryWeights, isAdjustMaxWeight = False):
        """Function used to adjust for individual country weights based on particular categories
                - isAdjustMaxWeight: Any NSBL Country weights should never be bigger than the max of SBL country weights, if so, adjust the country weights
                - isAdjustChinaExposure: per President.Jin in April 2019 BOD, the Total exposure of China can not exceed 10%. we will set 10% of 10% as buffer
                    thus the max of CHina country weights will be 9.9%
        """
        weightsToAdjust = 0
        newCountryWeightDict = {}
        countriesToAdjustLocal = []
        
        print("total weights origin: {0}".format(sum(list(countryWeights.values()))))
        if isAdjustMaxWeight:
            #1. get the sum of aggregrated extra weights for those overweighted countries comparing with max(sbl(any_countries)
            #2. get the new weights of the overweighted countries as the max(SBL)
            for country, weight in countryWeights.items():
                if weight > self.maxWeight_SBL:
                    #self.countriesToAdjust.append(country) #get overweighted country list as countries to adjust
                    countriesToAdjustLocal.append(country) #get overweighted country list as countries to adjust
                    weightsToAdjust = weightsToAdjust + (weight - self.maxWeight_SBL) #get aggregrated extra weights over max(SBL) for all countries
                    newCountryWeightDict[country] = self.maxWeight_SBL #set current overweighted country to use the max(SBL) as new weight

            chinaLimit = RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('China',0).get('NSBL',0)
            if countryWeights.get('CHN', 0) >= (chinaLimit - chinaLimit * 0.1):
                #threshold for check if china already in a warning area which are not appliable for adjustment pool
                self.countriesToAdjust.append('CHN')
                newCountryWeightDict['CHN'] = countryWeights.get('CHN', 0)

        else:
            raise("No Adjustment Choice Made, please double check your code!")
        
        #if no country weights to be adjusted, return the input countryWeights        
        if not newCountryWeightDict:
            return countryWeights
        
        #proportionally adjust the rest country weights by applying the aggregrated extra weights to their original proportion within the sub country group excluding the overweighted countries
        sumWeights_ExcludeAdjustCountry = sum(weight for country, weight in countryWeights.items() if country not in (countriesToAdjustLocal + self.countriesToAdjust))
        originalWeightPropotion_ExcludeAdjustCountry = { country : weight/sumWeights_ExcludeAdjustCountry for country, weight in countryWeights.items() if country not in (countriesToAdjustLocal + self.countriesToAdjust)}
        for country, originalWeight in countryWeights.items():
            if country in (countriesToAdjustLocal + self.countriesToAdjust):
                continue

            newWeight = originalWeightPropotion_ExcludeAdjustCountry.get(country) * weightsToAdjust + originalWeight#countryWeights.get(country)
            newCountryWeightDict[country] = newWeight
        
        #attatch adjusted countries to the list for the use of excluding them from the weighted average adjustment
        self.countriesToAdjust = self.countriesToAdjust + countriesToAdjustLocal 
        retCountryWeights = dict(sorted(newCountryWeightDict.items(), key=lambda kv: kv[1], reverse=True)) #return the sorted weighted countries by decending order
        retCountryWeights = self.updateCountryWeights(retCountryWeights)
        retCountryWeightsList = list(newCountryWeightDict.values())
        print("total weights: {0}".format(sum(list(retCountryWeights.values()))))

        return retCountryWeightsList, retCountryWeights 

    def adjust_WeightedAverageRating(self, countryWeightsDict, highRatingCountryWeightDict, lowRatingCountryRatingDict):
        """adjust weighted average rating separately by regional and non-regional
        """
        non_RegMemberList = self.nonRegional_NSBLMembers
        regMemberList = self.utils.getMemberList(isGetRegional = True, isGetSBL = False)

        ctyWeightsDict_Left_Over = {k:w for k,w in countryWeightsDict.items() if k in self.countriesToAdjust }

        #Adjust Regional
        ctyWeightsDict_Regional = {k:w for k,w in countryWeightsDict.items() if k in regMemberList}
        highRatingCountryWeight_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesToAdjust + non_RegMemberList))
        lowRatingCountryRtgDict_Regional = self.utils.getLowRatingCountryDict(isGetSBL = False, countriesNotInclude = (self.countriesToAdjust + non_RegMemberList))
        isWeightedAverageRatingExceeded_Regional = self._validateWeightedAverageRatingLimit(ctyWeightsDict_Regional)
        new_ctyWeightsDict_Regional = ctyWeightsDict_Regional
        while isWeightedAverageRatingExceeded_Regional:
            weightsDict_Regional = self._adj_Rtg_By_Regions(new_ctyWeightsDict_Regional, highRatingCountryWeight_Regional, lowRatingCountryRtgDict_Regional)
            isWeightedAverageRatingExceeded_Regional = self._validateWeightedAverageRatingLimit(weightsDict_Regional[1])
            new_ctyWeightsDict_Regional = weightsDict_Regional[1]
            highRatingCountryWeight_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = new_ctyWeightsDict_Regional, countriesNotInclude = (self.countriesToAdjust + non_RegMemberList))

        #Adjust NonRegional
        ctyWeightsDict_Non_Regional = {k:w for k,w in countryWeightsDict.items() if k in non_RegMemberList}
        highRatingCountryWeight_Non_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesToAdjust + regMemberList))
        lowRatingCountryRtgDict_Non_Regional = self.utils.getLowRatingCountryDict(isGetSBL = False, countriesNotInclude = (self.countriesToAdjust + regMemberList))
        isWeightedAverageRatingExceeded_Non_Regional = self._validateWeightedAverageRatingLimit(ctyWeightsDict_Non_Regional)
        new_ctyWeightsDict_Non_Regional = ctyWeightsDict_Non_Regional
        while isWeightedAverageRatingExceeded_Non_Regional:
            weightsDict_Non_Regional = self._adj_Rtg_By_Regions(new_ctyWeightsDict_Non_Regional, highRatingCountryWeight_Non_Regional, lowRatingCountryRtgDict_Non_Regional)
            isWeightedAverageRatingExceeded_Non_Regional = self._validateWeightedAverageRatingLimit(weightsDict_Non_Regional[1])
            new_ctyWeightsDict_Non_Regional = weightsDict_Non_Regional[1]
            highRatingCountryWeight_Non_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = new_ctyWeightsDict_Non_Regional, countriesNotInclude = (self.countriesToAdjust + regMemberList))

        finalCtyWeightsDict = self.utils.merge_dicts(new_ctyWeightsDict_Regional, new_ctyWeightsDict_Non_Regional)
        finalCtyWeightsDict = self.utils.merge_dicts(finalCtyWeightsDict, ctyWeightsDict_Left_Over)
        finalCtyWeightsList = list(finalCtyWeightsDict.values())
        print("total weights: {0}".format(sum(finalCtyWeightsList)))
        if sum(finalCtyWeightsList) > 1:
            #post adjustment for weights if total weights bigger than 1 due to accumulated decimal or rounding
            finalCtyWeightsList = { country : weight/sum(finalCtyWeightsList) for country, weight in finalCtyWeightsDict.items() }

        #udpate the country weights as well as the weights
        finalCtyWeightsDict = self.updateCountryWeights(finalCtyWeightsDict)
        finalCtyWeightsList = list(finalCtyWeightsDict.values())
        return finalCtyWeightsList, finalCtyWeightsDict

    def _adj_Rtg_By_Regions(self, countryWeightsDict, highRatingCountryWeightDict, lowRatingCountryRatingDict):
        inputCountryList = list(countryWeightsDict.keys())
        adjustedHighRatingCountryWeightsDict = {}
        adjustedLowerRatingCountryWeightsDict = {}
        newCountryWeightDict = {}

        #adjust high rated countries rating excluding the max country pre-adjusted
        highRatingCountrySumWeights = sum(weight for country, weight in highRatingCountryWeightDict.items() if country not in self.countriesToAdjust)
        originalWeightPropotion_HighRatingCountry = { country : weight/highRatingCountrySumWeights for country, weight in highRatingCountryWeightDict.items() if country not in self.countriesToAdjust}

        #proportionally adjust the lower weighted country weights to those higher weighted countries
        tempHighCountryRatingDict = highRatingCountryWeightDict
        for country, rating in lowRatingCountryRatingDict.items():
            lowCountryWeight = countryWeightsDict.get(country)
            if not lowCountryWeight:
                #the current low rating country not in the target portofli ocuntry list
                continue

            if lowCountryWeight <= ADJUSTMENT_FACTOR_RISK_LIMIT:
                adjustedLowerRatingCountryWeightsDict[country] = lowCountryWeight 
                continue

            minWeightsPerRating = self.getMinRatingWeightDict.get(rating)
            if not minWeightsPerRating:
                #excewption handling for if rounding decmimal rating not in the list
                continue

            newLowCountryWeight = lowCountryWeight - ADJUSTMENT_FACTOR_RISK_LIMIT
            if newLowCountryWeight <= self.getMinRatingWeightDict.get(rating):
                #if adjusted rating below the min rating limit, then go to next country to do the adjustment
                continue

            adjustedLowerRatingCountryWeightsDict[country] = newLowCountryWeight #adjustment start from the worst rating with highest GDP country
            adjustedHighRatingCountryWeightsDict = {}
            for country, originalWeight in tempHighCountryRatingDict.items():
                if country in self.countriesToAdjust:
                    #For those countries adjusted individually in previous steps:
                    # - if they those countries are high rated countries
                    # - then remove them from the high rated country pool, means do not adjust them here
                    # - previous two steps means: 10% China and max(SBL) weight
                    adjustedHighRatingCountryWeightsDict[country] = originalWeight
                    continue

                if 'CHN' in list(tempHighCountryRatingDict.keys()):
                    chinaWeightTemp = tempHighCountryRatingDict['CHN']
                    chinaLimit = RISK_LIMIT_DICT_SPB_ASSUMPTIONS['China']['NSBL']
                    if (chinaWeightTemp < chinaLimit) and (chinaWeightTemp >= chinaLimit * 0.99):
                        #append china to make it not to be adjusted next time
                        self.countriesToAdjust.append('CHN')
                        #newCountryWeightDict['CHN'] = newWeight

                #adjust for the high rated countries
                newWeight = originalWeightPropotion_HighRatingCountry.get(country) * ADJUSTMENT_FACTOR_RISK_LIMIT + originalWeight
                adjustedHighRatingCountryWeightsDict[country] = newWeight


            #TODO: DEBUGGING purpose@
            #update temp high rating dict to adjusted high rating country weight dict
            #NOTE: This need to be udpated!!!! or else, the weights will decresding gradually
            tempHighCountryRatingDict = adjustedHighRatingCountryWeightsDict

        for country in inputCountryList:
            if adjustedHighRatingCountryWeightsDict.get(country): #weights from high rating country part
                newCountryWeightDict[country] = adjustedHighRatingCountryWeightsDict.get(country)
            elif adjustedLowerRatingCountryWeightsDict.get(country): #weights from low rating country part
                newCountryWeightDict[country] = adjustedLowerRatingCountryWeightsDict.get(country)
            else:
                newCountryWeightDict[country] = countryWeightsDict.get(country)

        print("total weights: {0}".format(sum(list(newCountryWeightDict.values()))))

        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        #self.utils.reOrderCountryWeightDict(newCountryWeightDict, reverse = True)
        newCountryWeightsList = list(newCountryWeightDict.values())
        return newCountryWeightsList, newCountryWeightDict

    def adjust_NonRegionalCountryWeights(self, countryWeightsDict, nonRegionalValidationResult):
        """In NSBL case, adjust the nonregional total country weights
        """
        newCountryWeightDict = {}
        adjusted_Non_Regional_CountryWeightDict = {}
        adjusted_Regional_CountryWeightDict = {}
        targetWeights = RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('Non_Regional').get('NSBL')

        nonRegionalCountriesInScope = list(nonRegionalValidationResult.keys())
        totalNonRegionalWeightsOrigin = sum(list(nonRegionalValidationResult.values()))
        adjustWeights = totalNonRegionalWeightsOrigin - targetWeights

        originalWeightPropotion_Non_Regional = { country : weight/totalNonRegionalWeightsOrigin for country, weight in countryWeightsDict.items() if country in nonRegionalCountriesInScope}  
        for country, weight in nonRegionalValidationResult.items():
            newWeight = originalWeightPropotion_Non_Regional.get(country) * targetWeights
            adjusted_Non_Regional_CountryWeightDict[country] = newWeight
        
        newCountryWeightDict = adjusted_Non_Regional_CountryWeightDict
        sumWeights_Regional = sum(weight for country, weight in countryWeightsDict.items() if country not in (nonRegionalCountriesInScope + self.countriesToAdjust))

        originalWeightPropotion_Regional = { country : weight/sumWeights_Regional for country, weight in countryWeightsDict.items() if country not in (nonRegionalCountriesInScope + self.countriesToAdjust)}
        for country, originalWeight in countryWeightsDict.items():
            if (country in nonRegionalCountriesInScope) or (country in self.countriesToAdjust):
                continue

            newWeight = originalWeightPropotion_Regional.get(country) * adjustWeights + originalWeight
            adjusted_Regional_CountryWeightDict[country] = newWeight

        newCountryWeightDict.update(adjusted_Regional_CountryWeightDict)
        #for those not to ajust couries, get their original weight back to final country weights
        for country in self.countriesToAdjust:
            newCountryWeightDict.update({country: countryWeightsDict[country]})

        newCountryWeightDict =  self.updateCountryWeights(newCountryWeightDict)
        #self.utils.reOrderCountryWeightDict(newCountryWeightDict, reverse = True)
        newCountryWeightsList = list(newCountryWeightDict.values())

        #self.countriesToAdjust = self.countriesToAdjust + list(nonRegionalValidationResult.keys())
        self.nonRegionalCountriesNotToAdjust = nonRegionalCountriesInScope
        return newCountryWeightsList, newCountryWeightDict


    def adjust_ChinaWeights(self, countryWeightsDict, highRatingCountryWeightExcludeChina):
        newCountryWeightDict = {}
        adjusted_ChinaCountryWeightDict = {}
        targetWeight = RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('China').get('NSBL')

        chinaOriginalWeight = countryWeightsDict.get('CHN', 0)
        weightToAdjust = chinaOriginalWeight - targetWeight

        sumWeights_HighRatingCountry_ExcludeChina = sum(weight for country, weight in highRatingCountryWeightExcludeChina.items() if country not in self.countriesToAdjust)
        originalWeightPropotion_HighRatingCountry_ExcludeChina = { country : weight / sumWeights_HighRatingCountry_ExcludeChina for country, weight in highRatingCountryWeightExcludeChina.items() if country not in self.countriesToAdjust}

        adjusted_ChinaCountryWeightDict['CHN'] = targetWeight
        for country, originalWeight in highRatingCountryWeightExcludeChina.items():
            if country in self.countriesToAdjust:
                continue

            newWeight = originalWeightPropotion_HighRatingCountry_ExcludeChina.get(country) * weightToAdjust + originalWeight
            adjusted_ChinaCountryWeightDict[country] = newWeight

        for country in self.fullCountryList:

            if adjusted_ChinaCountryWeightDict.get(country):
                newCountryWeightDict[country] = adjusted_ChinaCountryWeightDict.get(country)
            else:
                newCountryWeightDict[country] = countryWeightsDict.get(country)
        print('total weights: {0}'.format(sum( list(newCountryWeightDict.values()) )))
        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        #self.utils.reOrderCountryWeightDict(newCountryWeightDict, reverse = True)
        newCountryWeightsList = list(newCountryWeightDict.values())

        return newCountryWeightsList, newCountryWeightDict

    def _validate_limits(self, countryWeightsDict):
        isWeightedAverageRatingExceeded = self._validateWeightedAverageRatingLimit(countryWeightsDict)
        isChinaLimitExceeded = self._valiadateChinaLimit(countryWeightsDict)
        isOverMaxSbl = self._validateOverMaxSblLimit(countryWeightsDict, self.sblCountryWeightsDict)
        nonRegionalValidationResult = self._valiadateNonRegionalLimit(countryWeightsDict)
        isNonRegionalOverWeighted = any(nonRegionalValidationResult)

        while (isWeightedAverageRatingExceeded or  
                isChinaLimitExceeded or 
                    isOverMaxSbl or 
                        isNonRegionalOverWeighted):
            countryWeights = list(countryWeightsDict.values())
            countryWeightsDict = self.validate_and_adj_risk_weights(countryWeights, countryWeightsDict)

            isWeightedAverageRatingExceeded = self._validateWeightedAverageRatingLimit(countryWeightsDict)
            isChinaLimitExceeded = self._valiadateChinaLimit(countryWeightsDict)
            isOverMaxSbl = self._validateOverMaxSblLimit(countryWeightsDict, self.sblCountryWeightsDict)
            nonRegionalValidationResult = self._valiadateNonRegionalLimit(countryWeightsDict)
            isNonRegionalOverWeighted = any(nonRegionalValidationResult)

        return countryWeightsDict

    def validate_and_adj_risk_weights(self, countryWeights, countryWeightsDict):
        """Main process of the adjustment: 
                To adjust NSBL country DOB weights to make sure the result country weights still fits for risk limits in Risk Appetite Statement
        """
        #validate china limit
        isChinaLimitExceeded = self._valiadateChinaLimit(countryWeightsDict)
        if isChinaLimitExceeded:
            highRatingCountryWeight = self.utils.getHighRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = countryWeightsDict, countriesNotInclude = ( self.countriesToAdjust + self.nonRegionalCountriesNotToAdjust))
            highRatingCountryWeight.pop("CHN") #remove china from the high rating list
            countryWeights, countryWeightsDict = self.adjust_ChinaWeights(countryWeightsDict, highRatingCountryWeight)
        isChinaLimitExceeded = False

        #validate for nonregional limit
        nonRegionalValidationResult = self._valiadateNonRegionalLimit(countryWeightsDict)
        isNonRegionalOverWeighted = any(nonRegionalValidationResult)
        if isNonRegionalOverWeighted:
            countryWeights, countryWeightsDict  = self.adjust_NonRegionalCountryWeights(countryWeightsDict, nonRegionalValidationResult)
        isNonRegionalOverWeighted = False

        #adjust country weights to see if any country have weights that bigger than the max(SBL), if so adjust it to other countries proportionally
        isOverMaxSbl = self._validateOverMaxSblLimit(countryWeightsDict, self.sblCountryWeightsDict)
        if isOverMaxSbl:
            countryWeights, countryWeightsDict = self.adjustNSBLIndividualCountryExposure(countryWeightsDict, isAdjustMaxWeight = True)
            isOverMaxSbl = False

        isWeightedAverageRatingExceeded = self._validateWeightedAverageRatingLimit(countryWeightsDict)
        while isWeightedAverageRatingExceeded:
            highRatingCountryWeight = self.utils.getHighRatingCountryWeightsDict(isGetSBL = False, countryWeightsDictInput = countryWeightsDict, countriesNotInclude = self.countriesToAdjust)
            lowRatingCountryRtgDict = self.utils.getLowRatingCountryDict(isGetSBL = True, countriesNotInclude = self.countriesToAdjust )
            countryWeights, countryWeightsDict = self.adjust_WeightedAverageRating(countryWeightsDict, highRatingCountryWeight, lowRatingCountryRtgDict)
            isWeightedAverageRatingExceeded = self._validateWeightedAverageRatingLimit(countryWeightsDict)
        isWeightedAverageRatingExceeded = False

        #print(sum(list(countryWeightsDict.values())))
        countryWeightsDict = self._validate_limits(countryWeightsDict)

        print("Successfully draw result!")
        return countryWeightsDict
    
    def assign_country_weights_main(self):
        countryWeights = list(self.originalCountryWeights_NSBL.values())
        countryWeightsDict = self.validate_and_adj_risk_weights(countryWeights, self.originalCountryWeights_NSBL)
        countryWeights = countryWeightsDict.values()

        countryPDDict = self.utils.getCountryPDDict(isGetSBL = False)
        weightedAverageRating = sum([weight * countryPDDict.get(country,0) for country, weight in countryWeightsDict.items()]) / sum(countryWeights)

        #post adjustement for offseting the machine rounding errors
        currentTotal = sum(list(countryWeightsDict.values()))
        if currentTotal < 1:
            residual = 1 - currentTotal
            countryWeightsDict['IDN'] = countryWeightsDict['IDN'] + residual
        elif currentTotal > 1:
            {country:(weight/currentTotal) for country, weight in countryWeightsDict.items()} 

        countryWeights = countryWeightsDict.values()
        print("\n Final weighted average PD is: {0}".format(weightedAverageRating))
        print("\n Final Sum of Weights is: {0}".format(sum(list(countryWeights))))

        return countryWeightsDict

if __name__ == "__main__":
    
    sblWeights = {'IND': 0.28915801926546963, 'IDN': 0.1116191512722784, 'PAK': 0.0854505915951819, 'BGD': 0.07926370348201613, 'TUR': 0.07486712502250271, 'RUS': 0.0743401781238019, 'CHN': 0.057306170488955574, 'AZE': 0.037976059191560343, 'UZB': 0.03489426384715608, 'PHL': 0.023768973875682626, 'OMN': 0.018712169929012996, 'LKA': 0.018329002537784893, 'THA': 0.0161560023467454, 'GEO': 0.01610176140264387, 'VNM': 0.014848128706751028, 'BRA': 0.010152288137133581, 'NPL': 0.009159700118598695, 'EGY': 0.008071539466874741, 'KAZ': 0.005657427636439821, 'ZAF': 0.0027967527550827216, 'ROU': 0.0019548447796345165, 'PER': 0.0019510237490599834, 'HUN': 0.0012841523888444957, 'TJK': 0.001086419815292319, 'MAR': 0.0010073030335005712, 'ECU': 0.0008248691361390196, 'SRB': 0.0003316220930990797, 'CIV': 0.00022327391190815632, 'BOL': 0.00020022236652957574, 'FJI': 0.0001557669595394204, 'ARM': 0.00015508464971473887, 'ETH': 0.00014481095390410706, 'BLR': 0.0001357542477432926, 'MMR': 0.00013358568843937916, 'KGZ': 0.00013283482491912972, 'LAO': 0.00013065438367980452, 'TUN': 0.00012221738274497134, 'MDV': 0.00011477634335668403, 'ARG': 0.00010327597844763269, 'KEN': 9.980441235419081e-05, 'MNG': 9.806042093785972e-05, 'LBN': 9.56495258568877e-05, 'MDG': 9.20461013380821e-05, 'TLS': 9.094869896047962e-05, 'GIN': 8.39700564467669e-05, 'KHM': 8.197674164680444e-05, 'GHA': 7.882973707229792e-05, 'BEN': 7.42291777225542e-05, 'RWA': 7.313262851530923e-05, 'DZA': 6.365098531046819e-05, 'PNG': 4.90751649331827e-05, 'AFG': 4.064201991958807e-05, 'TGO': 3.852329441219036e-05, 'JOR': 3.320895768138612e-05, 'VUT': 2.6561329002671374e-05, 'WSM': 2.637666159361456e-05, 'DJI': 1.4767396258153172e-05, 'TON': 1.311138604303361e-05, 'COK': 3.933415812910083e-06}
    
    
    pBuilder = NonSBLPortfolioBuilder(sblWeights)
    outputPath = r'C:\temp\Non_Sovereign_Country_Weights_Target_Portfolio_{0}_{1}.xlsx'.format(PROJECTION_YEAR, int(round(datetime.datetime.now().timestamp(),0)))#r"//WF//Sharefolder//RM//LiangXue//test//country_weight_output_Test.xlsx"

    countryWeights = pBuilder.assign_country_weights_main()
    dataframe = pd.DataFrame([a for a in countryWeights.items()], columns = ['Country','Weight'])
    dataframe.to_excel(outputPath, index = None, header=True, sheet_name='RawResult')