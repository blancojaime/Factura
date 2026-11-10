<service>
  <id>SICOM-MUNI</id>
  <name>SICOM-MUNI</name>
  <description>Sistema Integrado de Contratación Menor Municipal (servidor web)</description>
  <executable>@INSTALL@\python\python.exe</executable>
  <arguments>-m app.servidor</arguments>
  <workingdirectory>@CONFIG@</workingdirectory>
  <depend>SICOM-MUNI-BD</depend>
  <startmode>Automatic</startmode>
  <env name="PYTHONUTF8" value="1" />
  <env name="SICOM_GTK_DIR" value="@INSTALL@\gtk\bin" />
  <env name="FONTCONFIG_FILE" value="@CONFIG@\fonts.conf" />
  <env name="PATH" value="@INSTALL@\gtk\bin;%PATH%" />
  <logpath>@DATA@\logs</logpath>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>8</keepFiles>
  </log>
  <onfailure action="restart" delay="5 sec" />
  <onfailure action="restart" delay="10 sec" />
  <onfailure action="restart" delay="30 sec" />
  <resetfailure>1 hour</resetfailure>
  <stoptimeout>20 sec</stoptimeout>
</service>
