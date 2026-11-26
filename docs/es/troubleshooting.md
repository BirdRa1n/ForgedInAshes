[← Inicio de la documentación](README.md) · [English](../en/troubleshooting.md) · [Português (Brasil)](../pt-BR/troubleshooting.md) · **Español**

# 🩺 Solución de problemas

## El mod no carga

| Síntoma | Causa y solución |
|---|---|
| ForgedInAshes no aparece en la lista de *Mods* | La carpeta está en el lugar equivocado. Debe ser `<juego>/Mods/ForgedInAshes/ModInfo.xml` (sin carpetas repetidas). |
| El juego dice que la DLL del mod fue bloqueada | EasyAntiCheat está activado. Inicia el juego **sin EAC**. |
| Todo duplicado, errores de parches ya aplicados | Sigue instalada una copia antigua. Deja solo `Mods/ForgedInAshes`; borra `Mods/FerroEngrenagem` si existe. |
| Errores en rojo sobre `0Harmony` | Se borró `Mods/0_TFP_Harmony`. Verifica los archivos del juego en Steam para restaurarla. |

## Máquinas

| Síntoma | Causa y solución |
|---|---|
| La máquina dice que necesita torque | Su **toma de motor** está vacía. Pega un Electric Motor o trae un eje de una red de torque. |
| La red muestra **OVERLOADED** y se detiene tras 20 s | Las máquinas consumen más UT de las que ofrecen las fuentes. Añade fuentes, baja las RPM o divide la red con un **Clutch** o un **Torque Regulator**. |
| La red muestra **LOCKED** | Hay fuentes que giran una contra otra o a velocidades distintas. Gira una, añade un **Spin Inverter** o iguala las velocidades con una **Speed Box**. |
| Giro equivocado en una máquina | Gira el motor o añade un **Spin Inverter**. |
| El motor dice *No water* / *No Lubricant* | Lleva agua por tubería al motor y pon Lubricant en sus ranuras. |

## Fluidos

| Síntoma | Causa y solución |
|---|---|
| La tubería muestra **BLOCKED** | Dos fluidos distintos se encontraron en la misma red. Sepáralos o usa un **Fluid Separator**. |
| La tubería **pierde** | Presión por encima del límite: 4 bar en la **Pipe**, 12 bar en la **High Pressure Pipe**. Usa tuberías de alta presión o una **Relief Valve**. |
| El calderín dice *No lit Boiler Firebox touching this drum* | Pega un hogar encendido al calderín, mejor **debajo**. El hogar solo quema mientras un calderín pide calor, así que necesita combustible. |
| El Sap Tapper dice que su espalda debe tocar un tronco | Gíralo para que la **espalda** quede contra el tronco; el látex sale por el frente. |

## Cintas

| Síntoma | Causa y solución |
|---|---|
| Los objetos se detienen en una máquina (*not taken, it waits*) | La entrada de la máquina está llena o no usa ese objeto en la receta actual. |
| La cinta no se mueve | Sin torque: pon un eje junto a cualquier cinta de la línea (8 UT por cinta). |
| El embudo no hace nada | Espera mientras el cofre está abierto o la cinta de enfrente está llena. |

## El texto al mirar desaparece

La lectura que aparece al mirar un bloque solo se muestra hasta **4 m** (**5 m** en las máquinas grandes).
Acércate. Si desaparece incluso pegado a la máquina, [informa del error](#informar-de-un-error) con tu registro: el
mod escribe diagnósticos detallados de este caso (líneas que empiezan por `ui watchdog` y `look probe`).

## Registros

| Archivo | Dónde |
|---|---|
| Registro del juego (Windows) | `%APPDATA%\7DaysToDie\logs\output_log_client__<fecha>.txt` |
| Líneas del mod | Cada línea escrita por el mod empieza por **`[ForgedInAshes]`** |

Para un registro mucho más detallado, crea un archivo vacío llamado **`debug.txt`** dentro de
`Mods/ForgedInAshes/` y reinicia el juego. Bórralo después: el registro detallado ocupa mucho.

## Informar de un error

Abre un issue en **[github.com/BirdRa1n/ForgedInAshes/issues](https://github.com/BirdRa1n/ForgedInAshes/issues)**
con:

1. Qué hiciste, qué esperabas y qué pasó.
2. Versión del juego y del mod (ver `Mods/ForgedInAshes/ModInfo.xml`).
3. El archivo `output_log_client__*.txt` **completo** de la sesión en la que ocurrió.
4. Una captura de pantalla, si es algo visual.

---

[← Guía de juego](gameplay.md) · Siguiente: **[Desarrollo →](development.md)**
