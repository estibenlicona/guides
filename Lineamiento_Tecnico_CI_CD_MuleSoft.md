
# 📘 Lineamiento Técnico de CI/CD para Soluciones MuleSoft

## 1. Propósito
Establecer los lineamientos técnicos mínimos para la implementación de CI/CD en soluciones MuleSoft, con el fin de reducir riesgos técnicos y operativos, estandarizar prácticas de construcción y despliegue, y asegurar trazabilidad, calidad y seguridad desde el pipeline.

Este documento no constituye un documento de gobierno de TI, sino un **lineamiento técnico** que materializa decisiones del Gobierno de TI y Arquitectura.

---

## 2. Alcance
**Aplica a:**
- Soluciones desarrolladas sobre MuleSoft
- Pipelines de CI/CD asociados
- Ambientes: desarrollo, test/certificación y producción

**Consideraciones:**
- Obligatorio para nuevas aplicaciones
- Aplicaciones existentes pueden adoptar progresivamente o declararse como deuda técnica

**Fuera de alcance:**
- Políticas corporativas
- Gobierno de portafolio
- Sanciones o gestión administrativa

---

## 3. Marco de referencia y alineación
Alineado con:
- Gobierno de TI
- Seguridad de la Información
- Arquitectura de Software
- Prácticas DevOps

---

## 4. Principios técnicos
1. Automatización sobre validaciones manuales  
2. Seguridad integrada al pipeline  
3. Trazabilidad extremo a extremo  
4. Consistencia entre equipos  
5. Transparencia frente a limitaciones técnicas  

---

## 5. Modelo general de CI/CD
El flujo CI/CD en MuleSoft se compone de:
- Integración Continua (CI)
- Certificación
- Entrega Continua (CD)

El despliegue es gestionado por MuleSoft Exchange, que publica y despliega sobre Kubernetes. Los equipos no interactúan directamente con AKS.

---

## 6. Lineamientos técnicos

### 6.1 Control de código y ramas
- Estrategia: feature → develop → test → master
- Ramas feature de vida corta
- Nombradas según HU o funcionalidad
- Eliminación posterior al merge
- Revisión por pares recomendada en equipos >2 devs

---

### 6.2 Integración continua (CI)
**Validaciones obligatorias:**
- Pruebas unitarias
- SonarCloud
- Cobertura mínima: 65%

**Decisión temporal:**
Dado el soporte limitado de Sonar para XML, las métricas se usan como referencia mientras no exista una herramienta con soporte real para MuleSoft.

---

### 6.3 Certificación
- Aprobación técnica requerida
- No se repite análisis Sonar
- Punto habilitador para release

---

### 6.4 Entrega continua y releases
Incluye:
- Aprobación de seguridad
- Pruebas de performance (en evaluación)
- Comité de cambios
- Aprobación técnica final

**Rollback (decisión temporal):**
Rollback manual mediante despliegue de un release anterior estable.

---

### 6.5 Seguridad
**Análisis estático:**
No existe herramienta efectiva actualmente.
Se acepta operar sin análisis estático de forma temporal.

**Análisis dinámico:**
- Ejecutado en certificación
- Sobre endpoints expuestos
- OAS exportado desde RAML como insumo opcional

---

### 6.6 Diseño de APIs
- RAML es el formato oficial
- OAS exportado aceptado con limitaciones
- Conversión RAML → OAS puede generar inconsistencias

---

### 6.7 Gestión de secretos
- No se almacenan en el repositorio
- Uso de Secure Files / Library
- Azure Key Vault

**Decisión técnica:**
Un Key Vault por aplicación y por ambiente (a documentar como ADR).

---

### 6.8 Artefactos y despliegue
- Artefacto: JAR
- Tamaño aproximado: 80–170 MB
- Exchange gestiona imagen, registro y despliegue
- Tiempo de build ~10–12 minutos (aceptable)

---

## 7. Reglas
- 🔴 Obligatorio: CI automatizado, pruebas, secretos fuera del repo
- 🔵 Transitorio: rollback manual, ausencia de análisis estático
- 🟡 Recomendado: revisión por pares, adopción progresiva

---

## 8. Manejo de excepciones
Las excepciones deben:
- Estar justificadas
- Tener vigencia definida
- Ser aprobadas por COE / Arquitectura

---

## 9. Roles y responsabilidades
- **Desarrollo:** calidad y cumplimiento del flujo
- **DevOps:** pipelines y herramientas
- **COE / Arquitectura:** definición y evolución del lineamiento
- **Seguridad:** validación de controles

---

## 10. Control del documento
- Tipo: Lineamiento Técnico
- Owner: COE / Arquitectura
- Versión: 1.0
- Estado: Vigente
