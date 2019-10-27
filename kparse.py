#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 13 15:28:54 2019

@author: aransil
"""

# Reserved
    # inputs, system
    # variable names can't have dots in them
    # variable names can't be 'this' or 'parent'
    # keys can't be numeric
    # operator and variable names may not contain spaces
    # must have spaces separating elements in prefix, may or may not have spaces
    # strings or elements in graph can't have same value as any operators
    # If want a string not to be read with prefix, start with /
    # Variable definitions embedded in prefix formulas must end with a key: var1.var2...varN.key
    # 'system' cannot be a node name
    # trailing commas are invisible
    # If you have a prefix expression inside a list, sub-expressions can't contain commas
    # If you have a list, can't add a space before first elem: [5,3] is ok but [ 5,3] is not

# Parse a string (which may or may not be a node value), relative to a node in a system
# Node and input arguments must be referenced to the top level of the system
def parse(system, node, toEval = None, inputs=[], previous=[]):
    
    # node and inputs are top-referenced (ie requires the absolute path within this system)
    # variables in prefix expressions (at node value or in toEval) are relative to the node (NOT top-referenced)
    # previous tracks reference variables we've already used; prevents infinite loops
        
    outDict = {'system' : system, 'referenced' : [], 'output' : [], 'operators' : [], 'wellDefined' : True, 'value' : None}
    # Output system because it may be changed during evaluation by '=' operations
    # referenced are variables that are used in this expression (but not evaluated sub-expressions; top-referenced) 
    # output are variables set by this expression (but not evaluated sub-expressions; top-referenced)
    # operators is a list of operators used in this expression (but not evaluated sub-expressions)
    # wellDefined determines whether the information in the system plus inputs suffices to evaluate this expression
    # value is the result of evaluating the expression
    
    # Find our starting place in the system
    referenceNode = followPath(system, node)
    
    # If this wasn't a valid path, print an error and return
    if referenceNode['path'] == None:
        print('Tried to find ' + node + ' but this wasn\'t a valid path.')
        return outDict
    
    # Evaluate toEval (preferred), or evaluate the expression at this node
    if toEval == None: 
        toEval = referenceNode['value']
        
    ########################## Case 1 ########################## 
    ########################## Handle cases in which toEval isn't a prefix expression
    
    # If toEval itself isn't a string or is the empty string, return it
    if not type(toEval) == str or toEval == '':
        outDict['value'] = toEval
        return outDict
    
    # If this string starts with //, return as value
    if toEval[0] == '//': 
        outDict['value'] = toEval
        return outDict
    
    # If this string is a bool, return it
    if toEval == 'True' or toEval == 'true':
        outDict['value'] = True
        return outDict
    if toEval == 'False' or toEval == 'false':
        outDict['value'] = False
        return outDict
    
    # If the string is a number, return it
    try:
        if float(toEval)*0 == 0 : 
            outDict['value'] =float(toEval)
            return outDict
    except: pass

    # If the entire string is a list, interpret as a list of strings and evaluate each
    # Use findParentheticalSubstring to make sure it's the whole string
    # Do not change the reference node when evaluating
    if toEval[0] == '[':
        
        # Find corresponding closed bracket
        listString = findParentheticalSubstring(toEval)
        
        # Do analysis if all of toEval is a list (otherwise don't know what to return)
        if len(listString[0]) == len(toEval):
            
            # The value we will output will be a list
            outDict['value'] = []
            
            # Use commas to denote elements of the list (so sub-expressions can't have them)
            splitString = toEval.split(',')
            for elem in splitString:
                
                # Remove leading and trailing characters
                while elem[0] in ['[', ' '] : elem = elem[1:len(elem)] 
                while elem[len(elem)-1] in [']', ' '] : elem = elem[0:len(elem)-1] 
                
                # Recursively evaluate this element and merge with outDict
                evaluatedElement = parse(system, node, elem, inputs, previous)
                outDict['system'] = evaluatedElement['system']
                outDict['referenced'] = removeRedundantValues(outDict['referenced'] + evaluatedElement['referenced'])
                outDict['output'] = removeRedundantValues(outDict['output'] + evaluatedElement['output'])
                outDict['operators'] = removeRedundantValues(outDict['operators'] + evaluatedElement['operators'])
                outDict['wellDefined'] = outDict['wellDefined'] and evaluatedElement['wellDefined']
                outDict['value'].append(evaluatedElement['value'])
        
        # Once we've recursively evaluated each element, return result
        return outDict
            
    
    # Try to evaluate the string as a path through the graph such as var1.var2...key
    # This is the only case where the reference node changes
    
    # Get an absolute path to the variable (sum of absolute node and relative variable paths)
    referenceNodeAbsolutePath = referenceNode['path']
    thisVarAbsolutePath = referenceNodeAbsolutePath + '.' + toEval

    # Clean up this path to make it non-redundant
    pathResult = followPath(system, thisVarAbsolutePath)
    
    # If this returned a valid path, evaluate whatever is there and return it
    if not pathResult['path'] == None:
        
        # Prevent infinite loops
        if not pathResult['path'] in previous:

            # Recursively evaluate whatever we find from the perspective of the new node
            result = parse(system, pathResult['path'], None, inputs, previous+[referenceNode['path']])
            
            # There was exactly one variable referenced here: the one we evaluated
            result['referenced'] = [pathResult['path']]
            
            # Don't pass on output or operators because we changed reference nodes
            result['output'] = []
            result['operators'] = []
            
            # We've evaluated this variable, so return the result
            return result
        
        # If on this branch we've evaluated using this reference node, error to prevent loop
        else:
            print('> ERROR: Evaluating ' + pathResult['path'] + ' would lead to loop')
            return outDict
        

    ########################## Case 2 ##########################
    ##### Evaluate as a prefix notation expression 'operator var1 var2... varN'
    
    # If we've gotten to this point, default to the expression not being well-defined
    outDict['wellDefined'] = False

    # Initialize remainder, which will act as the part of the string we haven't processed
    remainder = toEval
    
    # If it's a string and starts and ends with parens, remove pairs of parens
    while remainder[0]=='(' and remainder[len(remainder)-1]==')':

        # Remove start and end parentheses
        remainder = remainder[1:len(remainder)-1]
        
    # Now remove start and end spaces
    while remainder[0]== ' ' : remainder = remainder[1:len(remainder)]
    while remainder[len(remainder)-1]== ' ' : remainder[0:len(remainder)-1]
        
    # All the operators we know how to deal with
    operators = ['+', '-', '*', '/', '%', '==', '<', '<=', '>', '>=', '=', 'union', 'intersection', 'sum', 'pi', 'dot']
        
    # Treat remainder as 'operator var1 var2... varN' and get operator
    thisOperator = remainder.split(' ')[0]
    
    # Remove trailing commas from operator
    while thisOperator[len(thisOperator)-1] == ',' : thisOperator = thisOperator[0:len(thisOperator)-1]
    
    # If we looked for an operator and found it, evaluate as a prefix notation expression
    if thisOperator in operators:

        # Remove operator from remainder, and store in outDict
        remainder = remainder[len(thisOperator)+1 : len(remainder)]
        outDict['operators'].append(thisOperator)
        
        # Treat remainder as 'var1 var2... varN' and evaluate each variable
        # Keep a list for each var1...varN of whether it is evaluable and what its value is 
        variableEvaluable = []
        variableValues = []
        
        # Track output variable: whether we are expecting one (None) or not (False)
        outputVarPath = False
        if thisOperator == '=' : outputVarPath = None
        
        # Loop over the remainder while it's not empty. Don't simply split by ' ' because variables may be expressions
        while not remainder == '':
            
            # Remove leading spaces and leftover commas
            while remainder[0] == ' ' or  remainder[0] == ',' : remainder = remainder[1:len(remainder)]
            
            # If remainder starts with open parentheses
            if remainder[0] == '(':
                
                # Find substring to corresponding closed parentheses. remainderSplit[0] is this substring, remainderSplit[1] is the rest
                remainderSplit = findParentheticalSubstring(remainder)
                
                # Recursively evaluate that whole expression without shifting reference node
                sectionResult = parse(system, node, remainderSplit[0], inputs, previous) 
                   
                # Set remainder to the rest of the string (after closed parens and ' ')
                remainder = remainder[len(remainderSplit[0]):len(remainder)]
                    
                # Nested prefix expressions can't be set
                if outputVarPath == None:
                    outputVarPath = False
     
            # If the remainder does not start with open parens, evaluate it recursively
            else:
                
                # Get the variable and remove from remainder
                thisVar = remainder.split(' ')[0]
                remainder = remainder[len(thisVar) + 1 : len(remainder)]
                
                # Remove trailing commas
                while thisVar[len(thisVar)-1] == ',' : thisVar = thisVar[0:len(thisVar)-1]
                
                # Recursively evaluate whatever we've found, maintaining this as reference node
                sectionResult = parse(system, node, thisVar, inputs, previous)
            
                # If this is the first variable after parens, add to output
                if outputVarPath == None:
                    
                    # Find the path and store as output variable path
                    pathResult = followPath(system, node +'.'+ thisVar)
                    outputVarPath = pathResult['path']
                    
            # If any values were set while evaluating this expression, use them in the future
            system = sectionResult['system']
            outDict['system'] = system
            
            # Incorporate prefix notation params from nested expressions and varaibles
            if not thisOperator == '=' or (type(outputVarPath) == str and not outputVarPath in sectionResult['referenced']):
                outDict['referenced'] = removeRedundantValues(outDict['referenced'] + sectionResult['referenced'])
            outDict['output'] = removeRedundantValues(outDict['output'] + sectionResult['output'])
            outDict['operators'] = removeRedundantValues(outDict['operators'] + sectionResult['operators'])
            
            # Store outputs from this evaluation into the two lists
            variableEvaluable.append(sectionResult['wellDefined'])
            variableValues.append(sectionResult['value'])
                
        ########################## Evaluate the Expression ##########################
        ##### All variables have been assessed, so evaluate this bit of prefix notation based on the operator
        ##### We have one operator, a list of variables, and a list indicating whether vars are well-defined      
            
        if False in variableEvaluable:
            print('> Warning: part(s) of ' + toEval + ' not evaluable')
            
        # If the operator is equals, set the output variable to whatever the remaining var(s) evaluated as
        # And return that same value
        if thisOperator == '=':                
                
            # If we can evaluate all non-outputs, this is evaluable. Otherwise it's not
            if not False in variableEvaluable and len(variableValues) == 2:
                try:
                    outputValue = variableValues[1] # Second variable is the output
                    outDict['wellDefined'] = True
                    outDict['output'] = removeRedundantValues(outDict['output'] + [outputVarPath])
                    system = setValue(system, outputVarPath, outputValue)
                    outDict['value'] = outputValue
                except:
                    print('> ERROR: Problem setting ' + str(outputVarPath) + ' to ' + str(outputValue))
        
        # binaryOpsDict stores operator characters with their functions
        binaryOpsNumsDict = {'+':plus, 
                   '-':minus,
                   '*':multiply,
                   '/':divide,
                   '%':modulus,
                   '==':isEqual,
                   '<':lessThan,
                   '<=':lessThanOrEqual,
                   '>':greaterThan,
                   '>=':greaterThanOrEqual
                   }
                   
        binaryOpsSetsDict = {      
                   'union':union,
                   'intersection':intersection,
                   'dot':dot
                   }
        
        unaryOpsSetsDict = {'sum':sumfn,
                   'sigma':sumfn,
                   'pi':pifn,
                   'cardinality':cardinality
                   }
        
        result = {'value':None, 'wellDefined':False}
        
        # Unary operator must have exactly one argument
        if thisOperator in unaryOpsSetsDict:     
            if len(variableValues) == 1:
                result = operate(unaryOpsSetsDict, thisOperator, 1, variableEvaluable, variableValues)
            else:
                print('> ERROR: operator ' + thisOperator + ' needs exactly one argument; was given ' + str(variableValues))
            
        # (biop A B C ...) gives (A biop B) op C ...
        elif thisOperator in binaryOpsNumsDict:   
            result = operate(binaryOpsNumsDict, thisOperator, 2, variableEvaluable, variableValues)
            
        elif thisOperator in binaryOpsSetsDict:   
            if not False in variableEvaluable:
                func = binaryOpsSetsDict[thisOperator]
                result['value'] = func(variableValues[0], variableValues[1])
                result['wellDefined'] = True
        
        outDict['value'] = result['value']
        outDict['wellDefined'] = result['wellDefined']
                    
        # Needs to:
            # establish whether we have enough values defined to calculate
            # If possible, calculate value

    # If we haven't evaluated this (including we couldn't find an operator corresponding to it),
    # return toEval as the string we were evaluating or the string at this node/key location
    else:
        outDict['value'] = toEval
    
    outDict['system'] = system
    return outDict   

def operate(opDict, operatorSymbol, numArgs, variableEvaluable, variableValues):
    
    # Assumes all variables are required to evaluate
    # Operates on the first two, then if there are more operates on the remaining one at a time
    
    # Initialize the output
    outDict = {'value':None, 'wellDefined':False}
    
    # Determine what the operation is
    func = opDict[operatorSymbol]
    
    # If there aren't at least as many values as arguments, don't do anything
    if len(variableValues) < numArgs: 
        print('> ERROR: not enough values in ' + str(variableValues) + ' to perform ' + operatorSymbol + ' (need at least ' + numArgs + ' )')
        return outDict
            
    try:
        if not False in variableEvaluable:
            
            # Initialize the value depending on the number of arguments this operator takes
            if numArgs == 1: outputValue = func(variableValues[0])
            elif numArgs == 2: outputValue = func(variableValues[0], variableValues[1])
            
            # Operate on the remaining arguments (if any)
            if len(variableValues) > numArgs:
                for elem in variableValues[numArgs:len(variableValues)] : outputValue = func(outputValue, elem)
                
            # If this worked, update outDict. If there was an error above, we won't have updated the dict before try exits.
            outDict['value'] = outputValue
            outDict['wellDefined'] = True
            
    except:
        
        # If this failed, it may be because one or more of the values was a list and a float or string was expected
        #try:
        if not False in variableEvaluable:
            
            # Assume we are returning a list
            outputValue = []
            
            # If we are doing a unary operator over list elements and each elem is a list,
            # do the operatr on each elem and return a list of results
            if numArgs == 1:
                for elem in variableValues:
                    outputValue.append(func(elem))
                
            # If we are doing a binary operator over elements that may be lists or may not,
            # (1) distribute single nums over every list element
            # (2) match lists pairwise (like dot), fail if length mismatch
            elif numArgs == 2:
                
                # Initialize, may be list or not
                outputValue = variableValues[0]
                
                # Operate using every successive element of variableValues
                for elem in variableValues[1:len(variableValues)]:
                    
                    # Case where toOutput and elem are both numbers: operate
                    if not type(outputValue) is list and not type(elem) is list:
                        outputValue = func(outputValue, elem)
                    
                    # Case where toOutput is num, elem is list: distribute
                    elif not type(outputValue) is list and type(elem) is list:
                        for subElem in elem:
                            outputValue = func(outputValue, subElem)
                    
                    # Case where toOutput is list, elem is num: distribute
                    elif type(outputValue) is list and not type(elem) is list:
                        newOutput = []
                        for subVal in outputValue:
                            newOutput.append(func(subVal, elem))
                        outputValue = newOutput
                    
                    # Case where both are lists: operate on pairs (like dot notation)
                    elif type(outputValue) is list and type(elem) is list:
                        newOutput = []
                        for i, subVal in enumerate(outputValue):
                            newOutput.append(func(subVal, elem[i]))
                        outputValue = newOutput
                        
            # If this worked, update outDict.
            outDict['value'] = outputValue
            outDict['wellDefined'] = True
                
        # If both of these strategies failed (treating elements as individuals and lists), print an error
        #except:
        #        print('> ERROR: Problem performing ' + operatorSymbol + ' on ' + str(variableValues))
    
    return outDict

# Binary ops on numbers
def plus (A, B): return float(A) + float(B)
def minus (A, B): return float(A) - float(B)
def multiply(A, B): return float(A) * float(B)
def divide(A, B): return float(A) / float(B)
def modulus(A, B): return float(A) % float(B)
def isEqual(A, B): return float(A) == float(B)
def lessThan(A, B): return float(A) < float(B)
def lessThanOrEqual(A, B): return float(A) <= float(B)
def greaterThan(A, B): return float(A) > float(B)
def greaterThanOrEqual(A, B): return float(A) >= float(B)

# Binary ops on sets
def union(A,B):
    toReturn = []
    inputs = [A,B]
    for elem in inputs:
        if type(elem) is list: 
            toReturn = removeRedundantValues(toReturn + elem)
        else: 
            if not elem == None and not elem in toReturn: 
                toReturn.append(elem)
    return toReturn
def intersection(A,B):
    toReturn = []
    for elem in A:
        if elem in B: toReturn.append(elem)
    return toReturn
def dot(A,B):
    toReturn = 0;
    for i, elem in enumerate(A): toReturn += float(elem)*float(B[i])
    return toReturn

# Unary ops on sets
def sumfn(A):
    toReturn = 0
    for elem in A: toReturn += float(elem)
    return toReturn
def pifn(A):
    toReturn = 0
    for elem in A: toReturn = toReturn*elem
    return toReturn
def cardinality(A):
    return len(A)
    
# Follows an input path through a system
# Returns the shortest version of this path plus whatever (value or node) we find there
# Node must be a node of the top-level system, otherwise it can't find it
def followPath(system, inputPath):
    
    # Initialize dict with return params
    toReturn = {'value' : None, 'path' : None}
    
    # Assume inputPath is of the form var1.var2...varN.key
    inputPathSplit = inputPath.split('.')
    
    # We can't count on (1) nodes having unique names or (2) nodes keeping track of their parents
    # so we need to track the absolute path through the system in order to backtrack when necessary
    pathList = []
    
    # First node entry must be a top-level node in the system
    if not inputPathSplit[0] in system: return toReturn
    
    # Orient ourselves to this top node
    nodeName = inputPathSplit.pop(0)
    currentNode = system[nodeName]
    
    # Path tracks path to this node; will be the same as node path except for this and parent elements (so it might be shorter)
    pathList.append(nodeName)
    
    # Go down the rabbit hole of nested node values
    while len(inputPathSplit)>0:

        # If the next entry is a key in this node, shift focus to that
        inputPathSplitInNode = False
        if type(currentNode) == dict:
            if inputPathSplit[0] in currentNode: 
                inputPathSplitInNode = True
                nodeName = inputPathSplit.pop(0)
                currentNode = currentNode[nodeName]
                
                # Also track the path we are taking
                pathList.append(nodeName)
        
        # If we didn't shift focus within the dict, doesn't matter if it's a dict
        if not inputPathSplitInNode:
            
            # If we have this.parent or this.input1, doesn't change focus or path
            if inputPathSplit[0] == 'this': inputPathSplit = inputPathSplit[1:len(inputPathSplit)]
            
            # If next direction is parent, go up one level by following the absolute path down
            elif inputPathSplit[0] == 'parent' :
                
                # Remove parent from list of node elements
                inputPathSplit = inputPathSplit[1:len(inputPathSplit)]
                
                # Set the path list to go up one level, by removing current node
                pathList = pathList[0:len(pathList)-1]
                
                # Reset current node and follow the absolute path down
                currentNode = system
                if len(pathList)>0:
                    for elem in pathList[0:len(pathList)]:
                        currentNode = currentNode[elem]
                        
            # If we don't recognize inputPathSplit[0] as either a key or a navigation command, the path is wrong
            else:
                return toReturn          
    
    # Return whatever is stored in 'current node' as the value. May be a dict or some other sort of value.
    toReturn['value'] = currentNode
    
    # Reconstruct the path (ie the full dot-notation name) out of the path list
    # This will be top-referenced, and the shortest path to this node
    nodePathString = ''
    for elem in pathList : nodePathString = nodePathString + elem + '.'
    nodePathString = nodePathString[0:len(nodePathString)-1] # Remove trailing period (always 1 char)
    toReturn['path'] = nodePathString
    
    return toReturn
    
# Sets value of path through nodes
# Path must be top-referenced but does not need to be the shortest path    
def setValue(system, path, value):
    
    # Find the path
    pathAnalysis = followPath(system, path)
    shortestPath = pathAnalysis['path']
    splitPath = shortestPath.split('.')
    currentNode = system
    
    # Follow the path
    for elem in splitPath[0:len(splitPath)-1] : 
        currentNode = currentNode[elem]
        
    # Set the element and return system
    currentNode[splitPath[len(splitPath)-1]] = value
    return system


# Assumes inputString starts with parens or brackets. Finds end parens/bracket and splits into list of two substrings
# First is full parenthetical, second is remainder minus any leading ' '
def findParentheticalSubstring(inputString):
    
    netParens = 0
    closeIndex = len(inputString)-1
    
    # Determine what type of symbol pair to use
    openSymbol = '('
    closeSymbol = ')'
    if inputString[0] == '[':
        openSymbol = '['
        closeSymbol = ']'
    elif inputString[0] == '{':
        openSymbol = '{'
        closeSymbol = '}'
    
    # Scan the string to see where we close the starting parentheses
    for i, c in enumerate(inputString):
        if c == openSymbol: netParens += 1
        elif c == closeSymbol: 
            netParens -= 1
            if netParens == 0: 
                closeIndex = i
                break
    
    # Return the whole string including leading and ending parens if we got to the end
    if closeIndex == len(inputString)-1: return [inputString[:closeIndex+1]]
    else:
        str1 = inputString[0:closeIndex+1]
        str2 = inputString[closeIndex+1:len(inputString)]
        if str2[0] == ' ': str2 = inputString[closeIndex+2:len(inputString)]
        return [str1, str2]
        
# Takes a list and removes duplicate values, so every value appears once
def removeRedundantValues(inputList):
    outputList = []
    
    for elem in inputList:
        #if outputList is []: outputList.append(elem)
        if not elem in outputList:
            outputList.append(elem)
            
    return outputList
        