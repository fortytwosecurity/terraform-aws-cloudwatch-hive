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


def hive_build_sechub_data(accountId, region, event, severityHive, reference,
                           tag_environment, tag_project, tag_company):
    finding = event['findings'][0]
    description = finding['Description'] + "\n\n A Security Hub finding has been detected: \n```json\n" + json.dumps(event, indent=4, sort_keys=True) + "\n```\n"  # noqa: E501

    title = "Security Hub (" + finding['Title'] + ") detected in " + accountId
    taglist = ["sechub", region, accountId, finding['Severity']['Label'].lower(),  # noqa: E501
               tag_environment, tag_project, tag_company]
    if finding['ProductFields'].get("RuleId"):
        taglist.append(finding['ProductFields']['RuleId'])
    if finding['ProductFields'].get("ControlId"):
        taglist.append(finding['ProductFields']['ControlId'])
    if finding['ProductFields'].get("ControlId"):
        taglist.append(finding['ProductFields']['aws/securityhub/ProductName'].replace(" ", ""))  # noqa: E501

    source = "sechub:" + region + ":" + accountId

    alert = Alert(title=title,
                  tlp=3,
                  tags=taglist,
                  description=description,
                  type='external',
                  source=source,
                  sourceRef=reference,
                  )

    print("Hive alert: ", alert)

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


def update_workflowstatus(boto3, finding):
    service_client = boto3.client('securityhub')
    try:
        response = service_client.batch_update_findings(
            FindingIdentifiers=[
                {
                 'Id': finding['Id'],
                 'ProductArn': finding['ProductArn']
                }
            ],
            Workflow={
               'Status': 'NOTIFIED'
            }
        )
        print(response)
        return response
    except Exception as e:
        print(e)
        print("Updating finding workflow failed, please troubleshoot further")
        raise


def create_issue_for_account(accountId, excludeAccountFilter):
    if accountId in excludeAccountFilter:
        return False
    else:
        return True


def lambda_handler(event, context):
    debug = False
    createHiveAlert = json.loads(os.environ['createHiveAlert'].lower())
    excludeAccountFilter = os.environ['excludeAccountFilter']
    debug = os.environ['debug']
    createHiveAlert = True

    if (debug): 
        print("event: ", event)

    # Get Sechub event details
    eventDetails = event['detail']
    finding = eventDetails['findings'][0]
    findingAccountId = finding["AwsAccountId"]
    findingRegion = finding["Region"]

    reference = event['id']
    severityHive = 1

    if createHiveAlert and create_issue_for_account(findingAccountId, excludeAccountFilter):  # noqa: E501
        hiveSecretArn = os.environ['hiveSecretArn']
        tag_company = os.environ['company']
        tag_project = os.environ['project']
        tag_environment = os.environ['environment']
        hiveSecretData = get_hive_secret(boto3, hiveSecretArn)
        hiveUrl = hiveSecretData['url']
        hiveApiKey = hiveSecretData['apikey']
        json_data = hive_build_sechub_data(findingAccountId, findingRegion, eventDetails,  # noqa: E501
                                           severityHive, reference,
                                           tag_environment, tag_project,
                                           tag_company)
        json_response = hive_rest_call(json_data, hiveUrl, hiveApiKey)
        print("Created Hive alert ", json_response)
        response = update_workflowstatus(boto3, finding)
        print("Updated sechub finding workflow: ", response)
