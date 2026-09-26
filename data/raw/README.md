# Dados brutos

Esta pasta recebe arquivos baixados diretamente da ANP.

Os arquivos de dados são ignorados pelo Git. O pipeline cria localmente um `manifest.json` contendo origem, horário de coleta, tamanho e SHA-256 de cada arquivo.

Nunca edite manualmente os arquivos desta pasta.


## Substituição segura de fontes

O diretório bruto não acumula versões antigas do mesmo dataset lógico.

A política é:

```text
baixar
-> validar conteúdo
-> remover somente artefatos antigos do mesmo dataset
-> gravar nova fonte
-> atualizar manifesto
```

Na camada por posto, isso cobre mudanças entre CSV e ZIP e também limpa diretórios de extração antigos.

Na série histórica agregada, a limpeza é feita por escopo, como Brasil, regiões, estados e municípios.

Arquivos pertencentes a outros datasets não são removidos.
