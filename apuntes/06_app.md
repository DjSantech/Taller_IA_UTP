### La aplicación: seis agentes y humano en una sola interfaz

La celda siguiente crea `ChessApp(AGENT_FACTORIES)` con los seis agentes del registro y «Humano» en los dos selectores, y la muestra. Así se abren los tres modos: humano contra humano, humano contra agente y agente contra agente (el uso está explicado en la sección 3, «Interfaz gráfica: `ChessApp`»).

Al ejecutar el cuaderno completo de forma automática no hay nadie que haga clic, así que la misma celda también **juega dos turnos por programa** (con los mismos métodos que llaman los botones). Con eso queda en la salida un tablero que ya tiene jugadas y su registro de decisiones. Para jugar de verdad hay que usar los controles en un Jupyter abierto con el kernel del taller: los widgets solo responden con un kernel en marcha.
