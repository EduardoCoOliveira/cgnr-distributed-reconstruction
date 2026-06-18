# Decisions

## Serviço C++ como HTTP independente

Decidi implementar a versão C++ como um serviço HTTP próprio, em vez de apenas um executável chamado pelo cliente. Isso deixa o projeto mais alinhado com a ideia de sistemas distribuídos: o cliente não precisa conhecer detalhes internos do processamento e conversa com Python e C++ usando o mesmo endpoint.

O trade-off é que o servidor HTTP em C++ fica mais simples do que um framework pronto, mas evita dependências extras e mantém o foco no requisito principal: C++17, CBLAS/OpenBLAS e CGNR implementado manualmente.

## CGNR como algoritmo principal e CGNE como opção

CGNR é obrigatório e foi tratado como algoritmo principal. CGNE também foi incluído porque o enunciado pede escolha de método se possível. Isso melhora a comparação acadêmica sem mudar o caminho principal da entrega.

## Regularização registrada sem alterar o CGNR obrigatório

O coeficiente de regularização `lambda = max(abs(H^T g)) * 0.10` é calculado e salvo nos metadados. A fórmula do CGNR exigida no enunciado foi mantida sem inserir termos extras no loop, porque alterar o passo iterativo mudaria o algoritmo pedido.

## Fator de redução por iteração de potência

O fator `c = ||H^T H||2` pode ficar caro para matrizes grandes. Usei iteração de potência para estimar a norma espectral sem materializar toda a matriz normal quando não for necessário. Isso reduz custo de memória e preserva a intenção matemática da métrica.

## Controle de saturação

Usei limite explícito de reconstruções simultâneas. Em Python o controle é feito com semáforo; em C++ com contador atômico. A ideia é falhar rápido com HTTP 429 quando o servidor estiver cheio, em vez de deixar a máquina ficar sem memória ou travar.

## Docker Compose com nomes de serviço

No Docker, o cliente não deve chamar `localhost`, porque isso apontaria para o próprio contêiner do cliente. Por isso deixei o cliente aceitar URLs por parâmetro e configurei o Compose para usar `python_server:8000` e `cpp_server:8001`. Isso mantém o mesmo cliente funcionando tanto localmente quanto em contêiner.

## Validação nativa C++ depende do ambiente

O código C++ foi preparado para CMake e OpenBLAS, mas a máquina não tinha essas dependências instaladas no momento da criação. A tentativa de instalar pelo Homebrew ficou presa no download do GCC e foi encerrada para não deixar processo pendente. A validação C++ deve ser retomada depois de instalar `cmake` e `openblas`, ou diretamente via Docker.

## Dataset de fumaça para validação rápida

Criei um dataset pequeno em `data/smoke/` usando uma matriz identidade 900x900 e um sinal 900x1. Isso não substitui o conjunto real do trabalho, mas valida o caminho completo de ponta a ponta: API, CGNR, geração de CSV/PNG, metadados, cliente e saturação.

Usei esse caminho porque reconstruir o conjunto 60x60 com `H-1.csv` é bem mais pesado e não é necessário para pegar erros de integração básicos.

## Fórmula de ganho ajustada pelo material de referência

O texto inicial tinha uma ambiguidade entre `sqrt(l*l)` e a fórmula mostrada no slide/PDF. Ajustei a implementação para usar `gamma_l = 100 + (1/20) * l * sqrt(l)`, porque é essa a expressão visível no material de referência da disciplina.

## Orientação da imagem e saídas PNG

A imagem de referência parece ter sido gerada em ambiente estilo MATLAB/Octave, onde `reshape` usa ordem por colunas. Ajustei Python e C++ para converter o vetor reconstruído em imagem usando ordem column-major. Isso deve evitar a aparência de imagem rotacionada em 90 graus.

Também passei a salvar dois PNGs: um PNG puro sem eixos, que é a imagem reconstruída limpa, e um PNG de visualização com escala logarítmica, título e eixos. O PNG com eixos ajuda no relatório e na comparação com o material de referência, mas o PNG puro continua sendo a saída principal do sistema.

## Contraste da visualização

A visualização inicial com log normalizava também o ruído de fundo, então a imagem parecia estática. Ajustei para usar `log(abs(f))` com contraste por percentis 75 e 99.9. Assim, valores fracos ficam próximos de preto e os refletores fortes ficam visíveis, mais parecido com a figura de referência.

Depois refinei essa visualização para reduzir pixels avulsos: o contraste passou a usar percentis 82 e 99.8, valores muito fracos são zerados, e pixels isolados sem vizinhos fortes também são removidos. Isso afeta apenas o PNG de visualização; o CSV e o PNG puro continuam representando a saída numérica da reconstrução.

Como a referência é essencialmente um mapa de pontos/refletores, substituí a visualização contínua por um `spot map`. A visualização agora calcula `log(abs(f))`, detecta máximos locais fortes, aplica uma distância mínima entre pontos e desenha apenas esses refletores em fundo preto. Essa escolha é só para apresentação visual e relatório; não altera o algoritmo CGNR nem os dados salvos em CSV.

## Novos sinais para imagens 2 e 3

Os sinais adicionais foram copiados para `data/` com nomes sem espaços para facilitar scripts e Docker. `G-2-image2.csv` tem escala parecida com `G-1`; `A-60x60-image3.csv` tem amplitude muito maior, então suas métricas residuais e valores reconstruídos ficam em outra ordem de grandeza. Mantive o mesmo pipeline para os dois para preservar comparabilidade.

## Otimização C++ por cache de matriz

O tempo total do C++ estava dominado pela leitura e parsing de `H-1.csv`, não pelo CGNR em si. O próprio metadado mostrava reconstrução numérica abaixo de 1 segundo, enquanto o total ficava perto de 40 segundos. Por isso adicionei cache em memória para a matriz `H` e para o fator de redução por `model_file`. A primeira requisição ainda paga o custo de leitura do CSV, mas requisições seguintes com o mesmo modelo reaproveitam a matriz carregada.

O trade-off é uso de memória maior enquanto o servidor estiver ativo, mas isso é aceitável para o requisito de reconstruir várias imagens no menor tempo possível com o mesmo modelo.
