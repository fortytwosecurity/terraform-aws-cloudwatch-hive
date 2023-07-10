import json
import boto3
import os
from thehive4py.api import TheHiveApi
from thehive4py.models import Alert


def hive_rest_call(alert, url, apikey):

    api = TheHiveApi(url, apikey)

    # Create the alert
    try:
        response = api.create_alert(alert)

        # Print the JSON response
        # print(json.dumps(response.json(), indent=4, sort_keys=True))

    except AlertException as e:  # noqa: F821
        print("Alert create error: {}".format(e))

    # Load into a JSON object and return that to the calling function
    return json.dumps(response.json())


def hive_build_alert_data(accountId, region, alarm, severityHive, reference,
                           tag_environment, tag_project, tag_company):
    description = alarm['state']['reason'] + "\n\n A cloudwatch alarm has fired: \n```json\n" + json.dumps(alarm, indent=4, sort_keys=True) + "\n```\n"  # noqa: E501
    alarmConfiguration = alarm['configuration']
    title = "Cloudwatch Alarm (" + alarm['alarmName'] + ") detected in " + accountId
    taglist = ["cloudwatch", region, accountId, alarm['alarmName'].lower(),  # noqa: E501
               tag_environment, tag_project, tag_company]
    if (alarmConfiguration['metrics'][0]['metricStat']['metric'].get("namespace")):
       taglist.append(alarmConfiguration['metrics'][0]['metricStat']['metric']['namespace'])
    source = "cloudwatch:" + region + ":" + accountId

    alert = Alert(title=title,
                  tlp=3,
                  tags=taglist,
                  description=description,
                  type='external',
                  source=source,
                  sourceRef=reference,
                  )
    return alert


def get_hive_secret(boto3, secretarn):
    service_client = boto3.client('secretsmanager')
    secret = service_client.get_secret_value(SecretId=secretarn)
    plaintext = secret['SecretString']
    secret_dict = json.loads(plaintext)

    # Run validations against the secret
    required_fields = ['apikey', 'url']
    for field in required_fields:
        if field not in secret_dict:
            raise KeyError("%s key is missing from secret JSON" % field)

    return secret_dict


def create_issue_for_account(accountId, excludeAccountFilter):
    if accountId in excludeAccountFilter:
        return False
    else:
        return True

def create_issue_for_alarm(alarmtName, excludeAlarmFilter):
    if alarmName in excludeAlarmFilter:
        return False
    else:
        return True

def lambda_handler(event, context):
    debug = False
    createHiveAlert = json.loads(os.environ['createHiveAlert'].lower())
    excludeAccountFilter = os.environ['excludeAccountFilter']
    excludeAlarmFilter = os.environ['excludeAlarmFilter']
    debug = os.environ['debug']

    if (debug): 
        print("event: ", event)

    # Get Sechub event details
    eventDetail = event['detail']
    alarmAccountId = event["account"]
    alarmRegion = event["region"]
    alarmName = event["alarmName"]
    reference = event['id']
    severityHive = 1

    if createHiveAlert and create_issue_for_account(alarmAccountId, excludeAccountFilter):  # noqa: E501
        if create_issue_for_alarm(alarmName,excludeAlarmFilter):
            hiveSecretArn = os.environ['hiveSecretArn']
            tag_company = os.environ['company']
            tag_project = os.environ['project']
            tag_environment = os.environ['environment']
            hiveSecretData = get_hive_secret(boto3, hiveSecretArn)
            hiveUrl = hiveSecretData['url']
            hiveApiKey = hiveSecretData['apikey']
            json_data = hive_build_alert_data(alarmAccountId, alarmRegion, eventDetail,  # noqa: E501
                                            severityHive, reference,
                                            tag_environment, tag_project,
                                            tag_company)
            json_response = hive_rest_call(json_data, hiveUrl, hiveApiKey)
            print("Created Hive alert ", json_response)


