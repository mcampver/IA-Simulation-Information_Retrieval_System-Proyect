"""
Script de verificación de dependencias para análisis de prompt engineering
=========================================================================
"""

import sys

def verificar_dependencias():
    """Verifica que todas las dependencias estén instaladas correctamente"""
    
    print("🔍 Verificando dependencias para análisis de prompt engineering...")
    print("=" * 60)
    
    dependencias = [
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("matplotlib", "Matplotlib"),
        ("seaborn", "Seaborn"),
        ("json", "JSON (estándar)"),
        ("pathlib", "Pathlib (estándar)"),
        ("datetime", "Datetime (estándar)"),
        ("re", "Regular Expressions (estándar)"),
        ("logging", "Logging (estándar)")
    ]
    
    resultados = []
    
    for modulo, nombre in dependencias:
        try:
            __import__(modulo)
            print(f"✅ {nombre:<20} - OK")
            resultados.append(True)
        except ImportError as e:
            print(f"❌ {nombre:<20} - ERROR: {e}")
            resultados.append(False)
    
    print("\n" + "=" * 60)
    
    if all(resultados):
        print("🎉 ¡Todas las dependencias están instaladas correctamente!")
        print("✨ El sistema de análisis de prompt engineering está listo para usar.")
        return True
    else:
        faltan = sum(1 for r in resultados if not r)
        print(f"⚠️  Faltan {faltan} dependencias por instalar.")
        print("\n💡 Para instalar las dependencias faltantes:")
        print("   pip install matplotlib>=3.5.0 seaborn>=0.11.0")
        return False

if __name__ == "__main__":
    verificar_dependencias()
