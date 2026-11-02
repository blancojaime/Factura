using System.IO;
using System.Reflection;
using System.Windows.Controls;

namespace ComexBol.App.Vistas;

public partial class AcercaView : UserControl
{
    public AcercaView()
    {
        InitializeComponent();
        var v = Assembly.GetExecutingAssembly().GetName().Version;
        TxtVersion.Text = $"Versión {v?.Major}.{v?.Minor}.{v?.Build}";
        var dir = App.CarpetaDatos; TxtRuta.Text = Path.Combine(dir, "comex.db"); TxtLog.Text = Path.Combine(dir, "errores.log");
    }
}
