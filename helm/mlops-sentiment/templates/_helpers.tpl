{{/*
Expand the name of the chart.
*/}}
{{- define "mlops-sentiment.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "mlops-sentiment.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mlops-sentiment.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mlops-sentiment.labels" -}}
helm.sh/chart: {{ include "mlops-sentiment.chart" . }}
{{ include "mlops-sentiment.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: sentiment-analysis
app.kubernetes.io/part-of: mlops-platform
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mlops-sentiment.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mlops-sentiment.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mlops-sentiment.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mlops-sentiment.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the image name
*/}}
{{- define "mlops-sentiment.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}

{{/*
Generate certificates secret name
*/}}
{{- define "mlops-sentiment.certificateSecretName" -}}
{{- printf "%s-certs" (include "mlops-sentiment.fullname" .) -}}
{{- end }}

{{/*
Generate environment variables
*/}}
{{- define "mlops-sentiment.env" -}}
{{- range $key, $value := .Values.deployment.env }}
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
{{- if .Values.deployment.secrets }}
{{- range $key, $value := .Values.deployment.secrets }}
{{- if $value }}
- name: {{ $key }}
  valueFrom:
    secretKeyRef:
      name: {{ include "mlops-sentiment.fullname" $ }}-secrets
      key: {{ $key }}
{{- end }}
{{- end }}
{{- end }}
{{- end }}
