import boto3, botocore, sys, json, datetime

cf = boto3.client("cloudformation")
s3 = boto3.client("s3")

def main(stack_name, environment, version, template_bucket_name = "zerobase-cloudformation-templates"):
    'Update or create stack'

    for template_name in ["database", "service"]:
        file_name = f"{template_name}.template"
        _parse_template(file_name)
        s3.upload_file(Bucket=template_bucket_name, Key=f"{environment}/api/{file_name}", Filename=file_name)

    template_data = _parse_template("main.template")
    parameter_data = _parse_parameters(f"{environment}.json")
    parameter_data.append({ "ParameterKey": "AppVersion", "ParameterValue": version })

    full_stack_name = f"{environment}-{stack_name}"
    params = {
        'StackName': full_stack_name,
        'TemplateBody': template_data,
        'Parameters': parameter_data,
        'Capabilities': ['CAPABILITY_IAM']
    }

    try:
        if _stack_exists(full_stack_name):
            print('Updating {}'.format(full_stack_name))
            stack_result = cf.update_stack(**params)
            waiter = cf.get_waiter('stack_update_complete')
        else:
            print('Creating {}'.format(full_stack_name))
            stack_result = cf.create_stack(**params)
            waiter = cf.get_waiter('stack_create_complete')
        print("...waiting for stack to be ready...")
        waiter.wait(StackName=full_stack_name)
    except botocore.exceptions.ClientError as ex:
        error_message = ex.response['Error']['Message']
        if error_message == 'No updates are to be performed.':
            print("No changes")
        else:
            raise
    else:
        print("CloudFormation template executed successfully.")
#         print(json.dumps(
#             cf.describe_stacks(StackName=stack_result['StackId']),
#             indent=2,
#             default=json_serial
#         ))


def _parse_template(template):
    with open(template) as template_fileobj:
        template_data = template_fileobj.read()
    cf.validate_template(TemplateBody=template_data)
    return template_data


def _parse_parameters(parameters):
    with open(parameters) as parameter_fileobj:
        parameter_data = json.load(parameter_fileobj)
    return parameter_data


def _stack_exists(stack_name):
    stacks = cf.list_stacks()['StackSummaries']
    for stack in stacks:
        if stack['StackStatus'] == 'DELETE_COMPLETE':
            continue
        if stack_name == stack['StackName']:
            return True
    return False


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


if __name__ == '__main__':
    main(*sys.argv[1:])
