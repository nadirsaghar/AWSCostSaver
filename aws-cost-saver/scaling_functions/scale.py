import json
import boto3
import os

HTML_CONTENT = '''
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="5">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">

    <title>Please wait</title>
  </head>
  <body>
    <div class="container" style="margin-top: 100px;">
        <div class="jumbotron">
            <div class="d-flex align-items-center">
                <h1 class="display-6" style="margin-right: 20px;">Your application is warming up</h1>
                <div class="spinner-border " role="status" aria-hidden="true"></div>
            </div>
            <p>Please wait while we load your application. You will be automatically redirected when the application is ready</p>
    </div>
  </body>
</html>
'''


def scale_out(event, context):
    ecs = boto3.client('ecs')
    ecs_service_name = os.environ['ECS_SERVICE_NAME']
    ecs_service_desired_count = int(os.environ['ECS_SERVICE_DESIRED_COUNT'])
    target_group_arn = os.environ['MAIN_APP_TARGET_GROUP']

    ecs_service_result = ecs.describe_services(services=[ecs_service_name])
    ecs_service = ecs_service_result['services'][0]
    if len(ecs_service['deployments']) == 1:
        primary_deployment = ecs_service['deployments'][0]
        if primary_deployment['runningCount'] > 0:
            set_target_group(target_group_arn)
        else:
            print(f'Updating ECS Service : setting task count to {ecs_service_desired_count}')
            ecs.update_service(
                service=ecs_service_name,
                desiredCount=ecs_service_desired_count
            )

    return {
        "statusCode": 200,
        "body": HTML_CONTENT,
        "headers": {
            "Content-Type": "text/html"
        }
    }


def scale_in(event, context):
    print('Performing Scale-in')
    ecs = boto3.client('ecs')
    ecs_service_name = os.environ['ECS_SERVICE_NAME']
    target_group_arn = os.environ['STANDBY_TARGET_GROUP_ARN']

    print('Updating ECS Service : setting task count to 0')
    ecs.update_service(
        service=ecs_service_name,
        desiredCount=0
    )
    set_target_group(target_group_arn)


def set_target_group(arn):
    print(f'Directing traffic to Target Group [{arn}]')
    alb = boto3.client('elbv2')
    rule_arn = os.environ['ALB_LISTENER_RULE_ARN']
    actions = [
        {
            'Type': 'forward',
            'TargetGroupArn': arn
        }
    ]

    conditions = [
        {
            'Field': 'path-pattern',
            'Values': ['/my-app*']
        }
    ]

    alb.modify_rule(
        RuleArn=rule_arn,
        Conditions=conditions,
        Actions=actions
    )
