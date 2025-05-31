from datetime import timezone
from rest_framework import serializers
from management.models import DeploymentStatusMessage, Deployment, Project



class DeploymentStatusMessageSerializer(serializers.ModelSerializer):
    timestamp_formatted = serializers.SerializerMethodField()

    class Meta:
        model = DeploymentStatusMessage
        fields = ['id', 'message', 'timestamp', 'timestamp_formatted']

    def get_timestamp_formatted(self, obj):
        if obj.timestamp:
            return obj.timestamp.astimezone(timezone.utc).strftime("%A, %B %d, %Y %H:%M:%S.%f")[:-3]
        return ''


class DeploymentSerializer(serializers.ModelSerializer):
    status_messages = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Deployment
        fields = ['id', 'commit_id', 'commit_url', 'status', 'created_at', 'created_at_formatted', 'updated_at', 'status_messages']

    def get_created_at_formatted(self, obj):
        if obj.created_at:
            return obj.created_at.astimezone(timezone.utc).strftime("%A, %B %d, %Y %H:%M:%S")
        return ''

    def get_status_messages(self, obj):
        messages = obj.status_messages.order_by('timestamp')
        return DeploymentStatusMessageSerializer(messages, many=True).data


class ProjectDeploymentSerializer(serializers.ModelSerializer):
    deployments = DeploymentSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_url', 'deployments']
