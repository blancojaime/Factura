using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;

namespace ComexBol.Presentation;

public abstract class ObservableObject : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;
    protected bool Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value; PropertyChanged?.Invoke(this, new(name)); return true;
    }
}

public sealed class RelayCommand(Func<object?, Task> run, Func<object?, bool>? can = null) : ICommand
{
    public RelayCommand(Func<Task> run) : this(_ => run()) { }
    public event EventHandler? CanExecuteChanged;
    public bool CanExecute(object? p) => can?.Invoke(p) ?? true;
    public async void Execute(object? p) => await run(p);
    public Task ExecuteAsync(object? p = null) => run(p);
    public void Refresh() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}
