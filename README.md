# Wikitree

Wikitree es una herramienta para generar arboles de relaciones en base al texto de páginas de Wikipedia.

Este proyecto es desarrollado para la entrega final de la cátedra de Text Mining de la Maestría de Ciencias de Datos de la Universidad Austral, cohorte 2020-2021. Los integrantes de para este proyecto son:

* Tomás Mena
* Bárbara Méndez
* Ligia Silombria
* Luciano Oberti
* Pablo Rodríguez

## Implementación

Wikitree construye redes de relaciones extrayendo entidades de artículos de Wikipedia y analizando los artículos de las entidades recursivamente.

Para la extracción de entidades, Wikitree utiliza la implementación base de extracción de entidades con BERT. La documentación del modelo, y el modelo mismo, se pueden acceder [aquí](https://huggingface.co/dslim/bert-base-NER).

La herramienta toma el query provisto por línea de comandos como el valor del nodo inicial y obtiene las entidades relacionadas a partir del artículo de Wikipedia para el mismo. Para cada nodo, se siguen los siguientes pasos:

1. Obtener el texto de la página de Wikipedia para el query inicial o la entidad relacionada.
2. Descartar secciones de "ver también", "referencias" y "vínculos externos".
3. Setear el nombre del nodo con el título del artículo. Si la entidad es de tipo distinto a PER, este es el último paso; de lo contrario continuar con el siguiente paso.
4. Extraer todas las entidades identificables en el texto utilizando BERT.
5. Rankeo de entidades candidato para expansión del grafo en función del número de apariciones en el texto.
6. Selección de las n entidades superiores hasta que se hayan agotado los candidatos, o que el número de entidades seleccionadas sea igual al deseado con al menos una entidad de tipo PER.
    * Descartar entidades que cumplan con cualquiera de las siguientes condiciones:
        * Son la misma entidad del nodo actual.
        * Tienen una longitud de un solo caracter.
        * No se corresponden con un token completo.
    * Si la entidad es de tipo persona y contiene una sola palabra, se aplica la lógica de promoción. Por esta lógica se priorizan ngramas por encima de entidades de una sola palabra para prevenir búsquedas que desambigüen a páginas de apellidos o primeros nombres.
7. Se repite el proceso para los nodos seleccionados.

## Instrucciones de uso

### Instalación

Para utilizar el proyecto se recomienda tener instalado el siguiente software como prerequisito:

* python3.8+
* pip
* virtualenv
* git

Para instalar el proyecto se recomienda clonar el repositorio en la rama main. Teniendo git instalado esto se puede hacer con el siguiente comando:

```
$ git clone https://github.com/tomasmmena/wikitree.git
```

Git creará un directorio con el contenido del projecto. Antes de ingresar al directorio se recomienda crear un ambiente virtual para instalar las dependencias. Esto se puede hacer con el siguiente comando:

```
$ virtualenv wikitree-venv
```

Esto inicializará un ambiente virtual donde se pueden instalar las dependencias de Wikitree sin interferir con otros proyectos. Para instalar las dependencias primero es necesario activar el ambiente virtual. En Windows esto se hace corriendo el archivo batch creado para este propósito en el directorio Scripts del nuevo ambiente:

```
> wikitree-venv\Scripts\activate
```

O en linux/mac:

```
$ source wikitree/bin/activate
```

Una vez activado el virtual environment, podemos ingresar al directorio del proyecto:

```
$ cd wikitree
```

Y finalmente instalar las dependencias:

```
$ pip install -r requirements.txt
```

Luego de que todos los paquetes se instalen estamos listos para utilizar Wikitree. Cada vez que quiera utilizar la herramienta deberá activar el ambiente virtual para hacerlo, pero no es necesario realizar la instalación de los requerimientos después de la primera sesión.

### Actualizar a una nueva versión

Estando en el directorio del proyecto y con el ambiente virtual activo, se puede hacer un pull de la última versión del código en github para actualizar el código:

```
$ git pull
```

Una vez actualizado el código, se deben instalar dependencias nuevamente en caso que algo haya cambiado en los requerimientos:

```
$ pip install -r requirements.txt
```

### Wikitree CLI

Para generar una red de relaciones simple, solamente es necesario setear el parámetro `query`. Por ejemplo, para obtener las relaciones del campeón mundial de ajedrez [Emanuel Lasker](https://en.wikipedia.org/wiki/Emanuel_Lasker), se puede utilizar el siguiente comando:

```
$ wikitree.py -q "Emanuel Lasker"
```

Wikitree procederá a construir un grafo nuevo en función del nodo inicial "Emanuel Lasker" y a expandirlo con los vecinos más cercanos. Una vez finalizado el proceso de extracción y análisis los resultados se abrirán en el navegador. La búsqueda se puede personalizar cambiando los valores de profundidad y ancho. En una búsqueda más ancha, para cada nodo se exploran más vecinos. En una búsqueda más profunda se exploran nodos más distantes. Por defecto estos parámetros están seteados en 2. Para buscar con ancho 5 y con profundidad 3 se setean los parámetros `width` y `depth` respectivamente:

```
$ wikitree.py -q "Emanuel Lasker" -w 5 -d 3
```

Wikitree soporta sesiones, que permiten guardar la información de un grafo para poder consultarlo después o para expandirlo posteriormente con búsquedas adicionales. Podemos tomar la búsqueda de Emanuel Lasker y guardarla en una sesión empleando el parámetro `session`:

```
$ wikitree.py -s chess -q "Emanuel Lasker" -w 5 -d 3
```

Una vez que el proceso termine y después de mostrar el grafo renderiazado en el navegador, Wikitree nos va a preguntar si queremos guardar la sesión. En caso afirmativo podemos recuperar la sesión guardada posteriormente corriendo el siguiente comando:

```
$ wikitree.py -s chess
```

Correr este comando va a hacer que Wikitree carge de la memoria el grafo correspondiente a la session `chess` y lo renderize nuevamente en el navegador. También podemos proveer una nueva query para expandir el grafo con nuevos nodos:

```
$ wikitree.py -s chess -q "Magnus Carlsen" -w 5 -d 3
```

El grafo resultante va a contener los nodos de ambas búsquedas resultando en un solo grafo conectado solamente si existen entidades en común.

## Limitaciones

Wikitree está a merced de la desambiguación de Wikipedia para muchas cosas. Es posible que una búsqueda por [Steve Jobs](https://en.wikipedia.org/wiki/Steve_Jobs) traiga muchas menciones de una entidad de tipo [organización llamada Apple](https://en.wikipedia.org/wiki/Apple_Inc.), pero si se realiza la búsqueda por esa entidad, el resultado va a ser [el artículo para la fruta](https://en.wikipedia.org/wiki/Apple). De momento, por esta razón el modelos solamente expande el grafo a través de entidades de tipo persona, donde a partir de la lógica de promoción hay mejores probabilidades de desambiguar correctamente con nombre y apellido. Esto tampoco es infalible, por ejemplo, [Paul McCartney](https://en.wikipedia.org/wiki/Paul_McCartney) tiende a presentar como vecino a [Linda Eastman](https://en.wikipedia.org/wiki/Linda_Eastman), en lugar de [Linda McCartney (née Eastman)](https://en.wikipedia.org/wiki/Linda_McCartney).

Artículos cortos también pueden generar problemas. Pocas menciones hacen que sea difícil determinar cuales son las más importantes entidades para continuar expandiendo el grafo. También hace que entidades para las que el modelo tiene menos confianza y que tienen una mayor probabilidad de pervertirse al desambiguar sean seleccionadas.
