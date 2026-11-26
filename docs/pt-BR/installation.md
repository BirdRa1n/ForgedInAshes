[← Início da documentação](README.md) · [English](../en/installation.md) · **Português (Brasil)** · [Español](../es/installation.md)

# 📥 Instalação

## Requisitos

| Requisito | Detalhes |
|---|---|
| Jogo | **7 Days to Die V3.4** (desenvolvido e testado na build **b10**) |
| Anti-cheat | **O EasyAntiCheat precisa estar desligado.** O mod tem uma DLL, que o EAC bloqueia. Use *Jogar sem EAC* no launcher ou abra o `7DaysToDie.exe` direto. |
| Harmony | Nada para instalar: o jogo já traz em `Mods/0_TFP_Harmony`. Mantenha essa pasta. |
| Modo | **Um jogador.** O multijogador ainda não foi testado. |

> [!WARNING]
> Nunca use mods com DLL em servidores oficiais ou protegidos pelo EAC. O ForgedInAshes é para os seus próprios
> mundos.

## Instalar

1. Baixe a versão mais recente (ou o repositório em ZIP) em
   **[github.com/BirdRa1n/ForgedInAshes](https://github.com/BirdRa1n/ForgedInAshes)**.
2. Abra a pasta do jogo. Na Steam: *Biblioteca → 7 Days to Die → botão direito → Gerenciar → Ver arquivos locais*.
3. Copie a pasta **`Mods/ForgedInAshes`** do download para a pasta **`Mods`** do jogo. O resultado deve ser:

   ```text
   7 Days To Die/
   └─ Mods/
      ├─ 0_TFP_Harmony/        (vem com o jogo)
      └─ ForgedInAshes/
         ├─ ModInfo.xml
         ├─ ForgedInAshes.dll
         ├─ Config/
         ├─ Data/
         ├─ Resources/
         └─ UIAtlases/
   ```

4. Abra o jogo **sem EAC**. No menu principal, abra *Mods*: **ForgedInAshes** deve aparecer na lista.

> [!TIP]
> Vai compilar do código-fonte? O `fe.bat mod` valida, compila e liga o repositório direto na pasta do jogo.
> Veja [Desenvolvimento](development.md).

## Começando um mundo

- **Mundos novos** são recomendados: o mod muda como a maioria dos itens é feita, e a progressão foi pensada para
  isso.
- **Mundos existentes** carregam normalmente — os blocos e itens novos só passam a existir.
- O mod guarda o estado de cada mundo (conteúdo das esteiras, fluidos, sinais, receitas fixas) em arquivos pequenos
  na pasta do save: `ForgedInAshes_belts.txt`, `ForgedInAshes_fluids.txt`, `ForgedInAshes_logic.txt` e
  `ForgedInAshes_autocraft.txt`.

## Configurações

`Mods/ForgedInAshes/Data/fe_settings.xml` guarda as opções. A principal:

| Opção | Valores | Efeito |
|---|---|---|
| `VanillaShortcuts` | `remove` (padrão) / `expensive` | `remove` tira as receitas de um clique do jogo que as cadeias de produção substituem. `expensive` as traz de volta custando **3×** mais, como opção de emergência. |

## Atualizar

1. Feche o jogo.
2. Troque a pasta `Mods/ForgedInAshes` pela nova (apague a antiga antes, não misture).
3. Abra o jogo. Seus mundos continuam funcionando.

### Vindo do *Ferro & Engrenagem*

O ForgedInAshes se chamava **Ferro & Engrenagem**. Os IDs de blocos e itens não mudaram, então seus mundos são
compatíveis:

1. Apague a pasta antiga `Mods/FerroEngrenagem` — **manter as duas carrega o mod duas vezes**.
2. Instale `Mods/ForgedInAshes` como acima.
3. Na primeira vez que cada mundo carregar, o mod renomeia sozinho os arquivos de estado antigos
   (`FerroEngrenagem_*.txt` → `ForgedInAshes_*.txt`). Esteiras, fluidos e sinais mantêm o conteúdo.

## Remover

> [!CAUTION]
> Tirar o mod de um mundo que tem blocos dele quebra esses blocos e pode corromper o save. Só remova em mundos
> onde você nunca colocou um bloco do ForgedInAshes, ou comece um mundo novo.

1. Feche o jogo.
2. Apague `Mods/ForgedInAshes`.

## Multijogador

| Cenário | Situação |
|---|---|
| Um jogador | ✅ Suportado |
| Partida com amigos (host) | ⚠️ Não testado — todos precisam da mesma versão do mod |
| Servidor dedicado | 🚧 Ainda não suportado — previsto para uma etapa futura |

---

Próximo: **[Guia de jogo →](gameplay.md)**
