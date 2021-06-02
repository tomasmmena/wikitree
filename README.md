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
    * Si la entidad es de tipo persona y contiene una sola palabra, se aplica la lógica de promoción.