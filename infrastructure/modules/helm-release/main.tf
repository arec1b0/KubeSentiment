resource "helm_release" "this" {
  name             = var.release_name
  chart            = var.chart_path
  namespace        = var.namespace
  create_namespace = true
  atomic           = true
  wait             = true

  values = var.values_files

  dynamic "set" {
    for_each = var.set_values
    content {
      name  = set.value.name
      value = set.value.value
    }
  }
}
