[← Inicio de la documentación](README.md) · [English](../en/installation.md) · [Português (Brasil)](../pt-BR/installation.md) · **Español**

# 📥 Instalación

## Requisitos

| Requisito | Detalles |
|---|---|
| Juego | **7 Days to Die V3.4** (desarrollado y probado en la build **b10**) |
| Antitrampas | **EasyAntiCheat debe estar desactivado.** El mod incluye una DLL, que EAC bloquea. Usa *Jugar sin EAC* en el lanzador o inicia `7DaysToDie.exe` directamente. |
| Harmony | No hay que instalar nada: el juego ya lo trae en `Mods/0_TFP_Harmony`. Conserva esa carpeta. |
| Modo | **Un jugador.** El multijugador todavía no se ha probado. |

> [!WARNING]
> Nunca uses mods con DLL en servidores oficiales o protegidos por EAC. ForgedInAshes es para tus propios mundos.

## Instalar

1. Descarga la última versión (o el repositorio en ZIP) desde
   **[github.com/BirdRa1n/ForgedInAshes](https://github.com/BirdRa1n/ForgedInAshes)**.
2. Abre la carpeta del juego. En Steam: *Biblioteca → 7 Days to Die → clic derecho → Administrar → Ver archivos
   locales*.
3. Copia la carpeta **`Mods/ForgedInAshes`** de la descarga en la carpeta **`Mods`** del juego. El resultado debe
   ser:

   ```text
   7 Days To Die/
   └─ Mods/
      ├─ 0_TFP_Harmony/        (viene con el juego)
      └─ ForgedInAshes/
         ├─ ModInfo.xml
         ├─ ForgedInAshes.dll
         ├─ Config/
         ├─ Data/
         ├─ Resources/
         └─ UIAtlases/
   ```

   **Los modelos 3D y las texturas son una descarga aparte:** en la misma versión, en *Assets*, descarga
   **`forgedinashes.unity3d`** y ponlo en `Mods/ForgedInAshes/Resources/` (el repositorio no lo incluye). Sin él
   el mod carga, pero las máquinas no tienen modelo.

4. Inicia el juego **sin EAC**. En el menú principal, abre *Mods*: **ForgedInAshes** debe aparecer en la lista.

> [!TIP]
> ¿Vas a compilar desde el código fuente? `fe.bat mod` valida, compila y enlaza el repositorio directamente en la
> carpeta del juego. Consulta [Desarrollo](development.md).

## Empezar un mundo

- Se recomiendan **mundos nuevos**: el mod cambia cómo se fabrica la mayoría de los objetos, y la progresión está
  pensada para ello.
- Los **mundos existentes** cargan sin problema: los bloques y objetos nuevos simplemente quedan disponibles.
- El mod guarda el estado de cada mundo (contenido de las cintas, fluidos, señales, recetas fijas) en archivos
  pequeños dentro de la carpeta de la partida: `ForgedInAshes_belts.txt`, `ForgedInAshes_fluids.txt`,
  `ForgedInAshes_logic.txt` y `ForgedInAshes_autocraft.txt`.

## Ajustes

`Mods/ForgedInAshes/Data/fe_settings.xml` contiene las opciones. La principal:

| Ajuste | Valores | Efecto |
|---|---|---|
| `VanillaShortcuts` | `remove` (predeterminado) / `expensive` | `remove` quita las recetas de un clic del juego que las cadenas de producción reemplazan. `expensive` las devuelve costando **3×** más, como opción de emergencia. |

## Actualizar

1. Cierra el juego.
2. Reemplaza la carpeta `Mods/ForgedInAshes` por la nueva (borra la antigua antes, no las mezcles).
3. Inicia el juego. Tus mundos siguen funcionando.

### Si vienes de *Ferro & Engrenagem*

ForgedInAshes antes se llamaba **Ferro & Engrenagem**. Los ID de bloques y objetos no cambiaron, así que tus mundos
son compatibles:

1. Borra la carpeta antigua `Mods/FerroEngrenagem`: **tener las dos carga el mod dos veces**.
2. Instala `Mods/ForgedInAshes` como se indica arriba.
3. La primera vez que cargue cada mundo, el mod renombra automáticamente los archivos de estado antiguos
   (`FerroEngrenagem_*.txt` → `ForgedInAshes_*.txt`). Las cintas, los fluidos y las señales conservan su contenido.

## Desinstalar

> [!CAUTION]
> Quitar el mod de un mundo que contiene sus bloques rompe esos bloques y puede corromper la partida. Desinstálalo
> solo en mundos donde nunca colocaste un bloque de ForgedInAshes, o empieza un mundo nuevo.

1. Cierra el juego.
2. Borra `Mods/ForgedInAshes`.

## Multijugador

| Escenario | Estado |
|---|---|
| Un jugador | ✅ Compatible |
| Partida con amigos (anfitrión) | ⚠️ Sin probar: todos necesitan la misma versión del mod |
| Servidor dedicado | 🚧 Aún no compatible, previsto para una etapa posterior |

---

Siguiente: **[Guía de juego →](gameplay.md)**
