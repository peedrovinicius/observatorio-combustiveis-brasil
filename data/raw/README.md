# Dados brutos

Esta pasta recebe arquivos baixados diretamente da ANP.

Os arquivos de dados são ignorados pelo Git. O pipeline cria localmente um `manifest.json` contendo origem, horário de coleta, tamanho e SHA-256 de cada arquivo.

Nunca edite manualmente os arquivos desta pasta.


## Substituição segura de fontes

O diretório bruto não acumula versões antigas do mesmo dataset lógico.

A política é:

```text
baixar
-> validar conteúdo externo
-> preparar e validar todo o dataset em staging
-> guardar a versão anterior em backup temporário
-> instalar a nova versão
-> restaurar a anterior se a instalação falhar
-> atualizar manifesto
```

Na camada por posto, isso cobre mudanças entre CSV e ZIP e também substitui diretórios de extração antigos. Um CSV interno inválido em um ZIP não remove a última versão válida do dataset.

Na série histórica agregada, Brasil, regiões, estados e municípios são tratados como um lote único junto com `history_manifest.json`. O snapshot anterior permanece íntegro se qualquer arquivo novo ou a instalação do lote falhar.

Arquivos pertencentes a outros datasets não são removidos.
