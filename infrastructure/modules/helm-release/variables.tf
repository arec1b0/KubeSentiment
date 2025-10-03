variable "release_name" {
  description = "The name of the Helm release."
  type        = string
}

variable "chart_path" {
  description = "The path to the Helm chart directory."
  type        = string
}

variable "namespace" {
  description = "The Kubernetes namespace to deploy into."
  type        = string
  default     = "default"
}

variable "values_files" {
  description = "A list of paths to Helm values files."
  type        = list(string)
  default     = []
}

variable "set_values" {
  description = "A list of values to set on the command line (e.g., {name=\"image.tag\", value=\"latest\"})."
  type        = list(object({
    name  = string
    value = string
  }))
  default     = []
}
