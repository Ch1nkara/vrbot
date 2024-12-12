import boto3
import os
import json
import ast
import time
from datetime import datetime, timezone

class SimpleDBWrapper:
  def __init__(self, domainName, localMode=False):
    self.domainName = domainName
    self.localMode = localMode
    self.localFile = 'storage.json'
    if not localMode:
      self.simpledb = boto3.client('sdb', region_name='us-east-1')
    self.create_domain()


  def create_domain(self):
    if self.localMode:
      if not os.path.exists(self.localFile):
        with open(self.localFile, 'w') as file:
          json.dump({}, file)
      with open(self.localFile, 'r') as file:
        data = json.load(file)
      if not self.domainName in data:
        data[self.domainName] = {}
        with open(self.localFile, 'w') as file:
          json.dump(data, file)
        #log('DEBUG', f"Domain '{self.domainName}' created locally.")
      else:
        #log('DEBUG', f"Domain '{self.domainName}' already exists.")
        pass
    else:
      self.simpledb.create_domain(DomainName=self.domainName)
      #log('DEBUG', f"Domain '{self.domainName}' created or exists in SimpleDB.")


  def delete_domain(self):
    if self.localMode:
      if not os.path.exists(self.localFile):
        with open(self.localFile, 'w') as file:
          json.dump({}, file)
      with open(self.localFile, 'r') as file:
        data = json.load(file)
      data.pop(self.domainName)
      with open(self.localFile, 'w') as file:
        json.dump(data, file)
      log('INFO', f"Domain '{self.domainName}' deleted locally.")
    else:
      self.simpledb.create_domain(DomainName=self.domainName)
      log('INFO', f"Domain '{self.domainName}' deleted in SimpleDB.")


  def put_attributes(self, DomainName, ItemName, Attributes):
    if self.localMode:
      with open(self.localFile, 'r') as file:
        data = json.load(file)
      if DomainName not in data:
        raise ValueError(f"Domain '{DomainName}' does not exist.")
      if ItemName not in data[DomainName]:
        data[DomainName][ItemName] = {}
      data[DomainName][ItemName].update({attr['Name']: attr['Value'] for attr in Attributes})
      with open(self.localFile, 'w') as file:
        json.dump(data, file)
      #log('DEBUG', f"Attributes for item '{ItemName}' updated locally in '{DomainName}'.")
    else:
      self.simpledb.put_attributes(
        DomainName=DomainName,
        ItemName=ItemName,
        Attributes=Attributes
      )
      #log('DEBUG', f"Attributes for item '{ItemName}' updated in SimpleDB '{DomainName}'.")


  def get_attributes(self, DomainName, ItemName):
    if self.localMode:
      with open(self.localFile, 'r') as file:
        data = json.load(file)
      if DomainName in data and ItemName in data[DomainName]:
        attributes = [
          {
            "Name": key, 
            "Value": str(value)
          } for key, value in data[DomainName][ItemName].items()
        ]
        return {"Attributes": attributes}
      else:
        return None
    else:
      return self.simpledb.get_attributes(
        DomainName=DomainName,
        ItemName=ItemName,
        ConsistentRead=True
      )


  def select(self, SelectExpression):
    if self.localMode:
      prefix = SelectExpression.split("LIKE '")[1].split("%'")[0]
      with open(self.localFile, 'r') as file:
        data = json.load(file)
      response = {"Items": []}
      for itemName, attributes in data.get(self.domainName, {}).items():
        if itemName.startswith(prefix):
            attributesList = [{"Name": key, "Value": value} for key, value in attributes.items()]
            response["Items"].append({
                "Name": itemName,
                "Attributes": attributesList
            })
      return response
    else:
      return self.simpledb.select(SelectExpression=SelectExpression)


  def getObj(self, itemName):
    response = self.get_attributes(DomainName=self.domainName, ItemName=itemName)
    if response:
      attributes = response.get('Attributes', [])
      return {attr['Name']: strToNum(attr['Value']) for attr in attributes}
    else:
      return None


  def setObj(self, itemName, itemJson):
    attributes = [
      {
        'Name': key, 
        'Value': str(value), 
        'Replace': True
      } for key, value in itemJson.items()
    ]
    self.put_attributes(DomainName=self.domainName, ItemName=itemName, Attributes=attributes)

  def getPaceNotes(self):
    query = f"SELECT * FROM `{self.domainName}` WHERE itemName() LIKE 'paceNote%'"
    rawNotes = self.select(SelectExpression=query)
    return [
      {attr['Name']: strToNum(attr['Value']) for attr in item['Attributes']}
      for item in rawNotes['Items']
    ]


  def setPaceNotes(self, paceNotes):
    for i, item in enumerate(paceNotes, 1):
      self.setObj(f"paceNote{i}", item)


def strToNum(value):
  # Handle integer
  try:
    return int(value)
  except ValueError:
    pass
  # Handle float
  try:
    return float(value)
  except ValueError:
    pass
  # Handle list of numeric (e.g., '[-53, 170.1253]')
  try:
    valueAsList = ast.literal_eval(value)
    if isinstance(valueAsList, list) and all(isinstance(i, (float, int)) for i in valueAsList):
      return [int(i) if i.is_integer() else float(i) for i in valueAsList]
  except (ValueError, SyntaxError):
    pass
  return value


def flushAndInit(domainName, boatData, trip, localMode=False):  
  sdb = SimpleDBWrapper('vrbot', localMode)
  sdb.delete_domain()
  sdb = SimpleDBWrapper('vrbot', localMode)
  sdb.setObj('boat', boatData)
  sdb.setObj('trip', trip)


def printDb(sdb):
  log('INFO', sdb.getObj('boat'))
  log('INFO', sdb.getObj('trip'))
  log('INFO', sdb.getPaceNotes())


def log(level, message):
  timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d-%Hh%Mm%SsZ")
  print(f"{timestamp} [{level}] {message}")


if __name__ == '__main__':
  flushAndInit('vrbot')
  sdb = SimpleDBWrapper('vrbot', True)
  printDb(sdb)
  #sdb.delete_domain()
