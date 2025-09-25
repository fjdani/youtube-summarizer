import sys
import pkg_resources

def diagnose():
    print("--- INICIANDO DIAGNÓSTICO DEL ENTORNO ---")
    
    # 1. Imprimir la versión de Python
    print(f"Versión de Python: {sys.version}")
    
    # 2. Intentar importar la librería y ver sus contenidos
    try:
        import youtube_transcript_api
        print("\nImportación de 'youtube_transcript_api' exitosa.")
        
        # 3. Imprimir la versión de la librería
        try:
            version = pkg_resources.get_distribution("youtube-transcript-api").version
            print(f"Versión de youtube-transcript-api: {version}")
        except Exception as e:
            print(f"No se pudo obtener la versión de la librería: {e}")

        # 4. Imprimir todos los atributos/funciones disponibles en la librería
        print("\nContenido del módulo 'youtube_transcript_api':")
        print("---------------------------------------------")
        print(dir(youtube_transcript_api))
        print("---------------------------------------------")

        # 5. Intentar acceder a la clase y ver su contenido
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            print("\nImportación de la CLASE 'YouTubeTranscriptApi' exitosa.")
            print("Contenido de la CLASE 'YouTubeTranscriptApi':")
            print("---------------------------------------------")
            print(dir(YouTubeTranscriptApi))
            print("---------------------------------------------")
        except ImportError:
            print("\nFALLO al importar la CLASE 'YouTubeTranscriptApi'.")

    except ImportError as e:
        print(f"\nERROR FATAL: No se pudo importar la librería 'youtube_transcript_api'.")
        print(e)
        
    print("\n--- DIAGNÓSTICO COMPLETADO ---")

if __name__ == "__main__":
    diagnose()
