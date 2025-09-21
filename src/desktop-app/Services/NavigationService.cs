using System;

namespace ArchBuilder.Services
{
    public class NavigationService
    {
        private static NavigationService _instance;
        public static NavigationService Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = new NavigationService();
                }
                return _instance;
            }
        }

        public event Action<object> NavigationRequested;

        private NavigationService() { }

        public void NavigateTo(object viewModel)
        {
            NavigationRequested?.Invoke(viewModel);
        }
    }
}

